################################################################################
# Superimpose the Random Component in the Bias Corrected IPET rainfall field
# September,2025
################################################################################
rm(list=ls(all=TRUE)) # clean the workspace and variables

# set working directory
setwd("C:/Users/ra1055/OneDrive - Princeton University/Desktop/Scripts_TCGenerator_rev/") 

##################
# Folders Info
#################
## Inputs_TCGenerator.csv - You have to populated this file with storm track(s) and their characteristics;
## USAtlanticCoastile - points along the coastline to be used as a reference throughout this script (No need to change)

# RandomFields
## GenSample.rds - 2,000 random component fields to be superimposed to the BIAS corrected TC rainfall field

# Results_Rainfall_Fields
## It will be created automatically after running the script
## RRF_hourly.rds: A list containing all hourly synthetic rainfall fields generated for all storms available in the "Inputs_TCGenerator.csv" file
## RRF_total.rds: similar to above, but synthetic rainfall accumulated fields
## nc_files : netcdf files from each one of the synthetic rainfall fields - name convention: RFF_"number of the generated sample"_"storm name + year"_"group number",grp.nc; Ex: RFF_3_FAY2008_1grp.nc 
### variables
### PRCP: hourly precipitation (in mm); Time (in seconds from 1970-01-01 00:00:00); lat: latitude; longitude
#############################################################################################################
# NOTE: To change the number of synthetic rainfall fields generated for one storm, go to line 116 ("gg.sim")
# By default, we set this number to 3 
#############################################################################################################

#############################
# Libraries and R packages
#############################
library(tidyverse)
library(raster)
library(reshape2)
library(pracma) #for 'meshgrid' function
library(geodist) # for geodist function
library(ncdf4) # creating netcdf files
library(sf) #library included to evaluate if a TC track "cuts" through a region
###################################
# (1) Global inputs and Parameters
###################################
# 1.1. Reference points and buffer window
ref.point <- data.frame(lon = -81.344, lat = 30.332) #lon/lat reference for Jacksonville, FL
win.size <- 5 #5 decimal degrees
win.rain <- 8 #8 decimal degrees (It was increased from 3dd to 8dd, The goal was to increase the footprint of the rainfall field)

############################
# 1.2. coastline - reference for landfalling TCs (Gori et al (2022) -  Nature Climate Change)
coast.pts <- read.csv("Inputs/USAtlanticCoastline.csv")
coast.pol <- rbind(coast.pts,c(coast.pts[nrow(coast.pts),]$Lon, coast.pts[1,]$Lat),coast.pts[1,])

############################
# 1.3. Create buffer window to identify TCs affecting Jacksonville, FL
lon.min <- ref.point$lon - win.size/2
lon.max <- ref.point$lon + win.size/2
lat.min <- ref.point$lat - win.size/2
lat.max <- ref.point$lat + win.size/2

lon.seq <- seq(lon.min,lon.max,0.1)
lat.seq <- seq(lat.min,lat.max,0.1)
lon.win.min = lon.seq[1]
lon.win.max = lon.seq[length(lon.seq)]
lat.win.min = lat.seq[1]
lat.win.max = lat.seq[length(lat.seq)]

df.window <- NULL
for(iv in 1:length(lat.seq)){
  df.window <- rbind(df.window, c(lon.min, lat.seq[iv]))
}
for(ih in 2:length(lon.seq)){
  df.window <- rbind(df.window, c(lon.seq[ih], lat.max))
}
for(iv in (length(lat.seq)-1):1){
  df.window <- rbind(df.window, c(lon.max, lat.seq[iv]))
}
for(ih in (length(lon.seq)-1):1){
  df.window <- rbind(df.window, c(lon.seq[ih], lat.min))
}
colnames(df.window) <- c("x","y")
df.window <- as.data.frame(df.window)

############################################
# 1.4. Create grid for IPET model output : 8 x 8 buffer window at 0.05dd spacing
lon.min_rain <- ref.point$lon - win.rain/2
lon.max_rain <- ref.point$lon + win.rain/2
lat.min_rain <- ref.point$lat - win.rain/2
lat.max_rain <- ref.point$lat + win.rain/2

r.grid <- raster(nrow = (lat.max_rain - lat.min_rain)/0.05+1, ncol = (lon.max_rain-lon.min_rain)/0.05+1, xmn=lon.min_rain, xmx=lon.max_rain, ymn=lat.min_rain, ymx=lat.max_rain)
df.grid.xy <- as.data.frame(r.grid,xy = TRUE)
df.grid.xy$x <- round(df.grid.xy$x,3)
df.grid.xy$y <- round(df.grid.xy$y,3)
n.grid <- nrow(df.grid.xy)

############################
# 1.5. create grid for running IPET
lons <- sort(unique(df.grid.xy$x))
lats <- sort(unique(df.grid.xy$y))
n.lon <- length(lons)
n.lat <- length(lats)

grids <- pracma::meshgrid(lons,lats)
lon.grids <- grids$X
lat.grids <- grids$Y

## identifying cells in the ocean
cells_PRCP <- as.data.frame(cbind(c(lon.grids), c(lat.grids)))
cells_sea.idx <- which(sp::point.in.polygon(cells_PRCP[,1],cells_PRCP[,2], coast.pol$Lon, coast.pol$Lat)==0) # 0 is in the ocean, 1 is on land
############################################################################
# 1.6. number of random components fields created prior running this script
nsim = 2000 # (do not change)

# 1.7. number of TC rainfall fields generated for each TC 
# numbers between 1 and 2000 can be selected
gg.nsim = 3 #(adjust, 1-2000)
order.sim.t <- array(NA,c(nsim,gg.nsim))
############################
# 1.8. creating directories to save outputs
dir.create("Results_Rainfall_Fields/")
dir.create("Results_Rainfall_Fields/nc_files/")
##################################################################################################
# (1) load TC tracks and characteristics: (see the provided template in "Inputs_TCGenerator.csv") 
##################################################################################################
# col1: storm ID: AL062008; (not required; only for referencing) 
# col2: name: FAY; (not required; only for referencing)
# col3-6: month, day, year and time: related to the position of the center of circulation (required, hourly)
# col7: lon: longitude of the center of circulation (obs: positive value, the correction will be made later in this script)
# col8: lat: latitude of the center of circulation
# col9: RMW: radius of maximum wind speed (required, in nm)
# col10: POCI: pressure of the outermost closed isobar (required, in mb)
# col11: PRESS.MIN: minimum pressure (required, in mb)
#TC.char_raw <- data.frame(read.csv("Inputs/Inputs_TCGenerator.csv"))
TC.char_raw <- data.frame(read.csv("Inputs/Inputs_TCGenerator.csv"))
colnames(TC.char_raw) <- c("STORM_ID","NAME","MONTH","DAY","TIME","YEAR","LAT","LON","RMW","POCI","PRESS.MIN")

##################################################################################################
# (1.1) Reformat the original raw TC characteristic data; 
# Compute the azimuth (i.e., TC direction)
# Compute IPET rainfall
##################################################################################################  
TC.ID.t <- unique(TC.char_raw$STORM_ID) # you can have more than one storm in the TC track and characteristics input file
TCrain.sim <- list()
TCrain.sim_hr <- list()
count_igr <- 0 # count the number of groups in the TC file. We highlight that one TC can have more than one group
df.TC.char <- data.frame(TC.order=NA, TC.year=NA, TC.name=NA, TC.group=NA, rainfall.total.IPET=NA,press.min=NA,v.tran=NA, AZ=NA)

for(iTC in 1:length(TC.ID.t)){
      
  TC.ID <- TC.ID.t[iTC]
  db.TC <- TC.char_raw %>% filter(STORM_ID==TC.ID) # subset TC characteristics 
  #db.TC$LON <- -db.TC$LON # correction for the longitude values. If you enter with negative values of "LON" as your inputs; comment this line
  TC.name <- db.TC$NAME[1]
  TC.year <- db.TC$YEAR[1]
      
  db.TC1 <- data.frame(NAME=db.TC$NAME, YEAR=db.TC$YEAR, MONTH=db.TC$MONTH, DAY=db.TC$DAY, TIME=db.TC$TIME,
                       LON=db.TC$LON, LAT=db.TC$LAT, RMW=db.TC$RMW,POCI=db.TC$POCI, PRESS.MIN=db.TC$PRESS.MIN)
      
  # I first screen the TC that has no required variables
  if(all(db.TC1$RMW == -99) ) next
  if(all(db.TC1$POCI == -99) ) next
  if(all(db.TC1$PRESS.MIN == -99) ) next
      
  ################################################################################################
  # Identifying track points within the 5dd box (more than two points)
  ################################################################################################
  indic.1 <- sp::point.in.polygon(db.TC1$LON, db.TC1$LAT, df.window$x, df.window$y) 
  db.TC2 <- db.TC1 %>% add_column(indic.buffer.TC=indic.1) # flag with 1 time steps in which the TC track is within the bounding box; 0 = outside bounding box 
  pos.1 <- which(indic.1!=0)
  
  ############################################################################################################################
  # Identifying if there is only a single track point (or zero "observed" points) within the 5dd box; but "cutting" the box
  ############################################################################################################################
  # Closest two points to the intersection with the 5dd box (Used as reference to compute IPET rainfall and bias)
  if(length(pos.1)<=1){ #box 1: 5dd
  
    track_coords <- data.frame(lon=db.TC1$LON,lat=db.TC1$LAT)
    storm_track <- st_as_sf(track_coords, coords = c("lon", "lat"), crs = 4326) |>
      summarise(geometry = st_combine(geometry)) |>   # combine points
      st_cast("LINESTRING")                           # make a line
    
    box1_coords <- data.frame(lon=df.window$x,lat=df.window$y)
    box1 <- st_as_sf(box1_coords, coords = c("lon", "lat"), crs = 4326) |>
      summarise(geometry = st_combine(geometry)) |>
      st_cast("POLYGON")
    
    switch_box1 <- st_intersects(storm_track, box1, sparse = FALSE) # verifying the presence of intersection between the track and the 5dd box
    if(switch_box1 == TRUE){
      
      boundary <- st_boundary(box1)             # box edges
      cross_pts <- st_intersection(storm_track, boundary)
      cross_pts <- st_cast(cross_pts, "POINT")
      
      # Identify the closest "observed point" to the intersection pts
      # number of points
      #(1) only a start;
      #(2) start and end;
      # Storm track points
      track_vertices <- st_coordinates(storm_track)   # matrix of lon/lat
      track_points <- st_as_sf(
        data.frame(track_vertices),
        coords = c("X", "Y"),
        crs = 4326
      )
      
      closest_vertices <- lapply(1:nrow(cross_pts), function(i) {
        d <- st_distance(cross_pts[i,], track_points)
        which.min(d)  # vertex closest to this intersection
        
      })
      
      pts_idx <- unique(unlist(closest_vertices)) # two different points (OK!)
      
      #()Especial case: Track stops within the box
      if(length(pts_idx) < 2){ # only a single point
        
        if(pts_idx != nrow(track_coords)){
          
          pts_idx <- c(pts_idx,(pts_idx+1)) # uses the next point of the storm track
      
        }else{
        
          pts_idx <- c(pts_idx,(pts_idx-1)) #If the closest point is the last point of the track, we pick the previous time step
        }
      } # end if-else single point
      
      pos.1 <- seq(from=min(pts_idx),to=max(pts_idx),by=1)
      indic.1[pos.1] <- 1
      db.TC2$indic.buffer.TC[pos.1] <- 1 # Points artificially placed within the buffer
      
    } # end if-else switch_box1
  } # end if-else box 1
  
  ################################################################################################
  #  Looking for track points intersecting the 8dd box - Not intersecting ("cutting") the 5dd box
  ################################################################################################
  # Closest two points to the intersection with the 8dd box (Used as reference to compute IPET rainfall and bias)
  if(length(pos.1)<=1){ #box 2: 5dd < track < 8dd
    
    track_coords <- data.frame(lon=db.TC1$LON,lat=db.TC1$LAT)
    storm_track <- st_as_sf(track_coords, coords = c("lon", "lat"), crs = 4326) |>
      summarise(geometry = st_combine(geometry)) |>   # combine points
      st_cast("LINESTRING")                           # make a line
    
    box2_coords <- data.frame(lon=c(min(df.grid.xy$x),max(df.grid.xy$x)),lat=c(min(df.grid.xy$y),max(df.grid.xy$y)))
    box2 <- st_as_sf(data.frame(
          lon = c(box2_coords$lon[1], box2_coords$lon[2], box2_coords$lon[2], box2_coords$lon[1], box2_coords$lon[1]),
          lat = c(box2_coords$lat[1], box2_coords$lat[1], box2_coords$lat[2], box2_coords$lat[2], box2_coords$lat[1])
        ),
        coords = c("lon", "lat"), crs = 4326) |>
          summarise(geometry = st_combine(geometry)) |>
          st_cast("POLYGON")
    
    switch_box2 <- st_intersects(storm_track, box2, sparse = FALSE) # verifying the presence of intersection between the track and the 5dd box
    if(switch_box2 == TRUE){
      
      boundary <- st_boundary(box2)             # box edges
      cross_pts <- st_intersection(storm_track, boundary)
      cross_pts <- st_cast(cross_pts, "POINT")
      
      track_vertices <- st_coordinates(storm_track)   # matrix of lon/lat
      track_points <- st_as_sf(
        data.frame(track_vertices),
        coords = c("X", "Y"),
        crs = 4326
      )
      
      # Identify the closest "observed point" to the intersection pts
      closest_vertices <- lapply(1:nrow(cross_pts), function(i) {
        d <- st_distance(cross_pts[i,], track_points)
        which.min(d)  # vertex closest to this intersection
        
      })
      
      pts_idx <- unique(unlist(closest_vertices)) # two different points (OK!)
      
      # Especial case: Track stops within the box
      if(length(pts_idx) < 2){ # only a single point
        
        if(pts_idx != nrow(track_coords)){
          
          pts_idx <- c(pts_idx,(pts_idx+1)) # uses the next point of the storm track
          
        }else{
          
          pts_idx <- c(pts_idx,(pts_idx-1)) #If the closest point is the last point of the track, we pick the previous time step
        }
      } # end if-else single point
      
      pos.1 <- seq(from=min(pts_idx),to=max(pts_idx),by=1)
      indic.1[pos.1] <- 1
      db.TC2$indic.buffer.TC[pos.1] <- 1 # Points artificially placed within the buffer
      
    } # end if-else switch_box2
  } # end if-else box 2
  
  ################################################################################################
  # Track does not "cut" any box
  ################################################################################################
  # Uses the two closest consecutive points to the 5dd box as a reference to compute IPET rainfall and variables for the bias corretion framework
  if(length(pos.1)<=1){ # track > 8dd
  
    track_coords <- data.frame(lon=db.TC1$LON,lat=db.TC1$LAT)
    storm_track <- st_as_sf(track_coords, coords = c("lon", "lat"), crs = 4326) |>
      summarise(geometry = st_combine(geometry)) |>   # combine points
      st_cast("LINESTRING")                           # make a line
    
    # Create a data frame with the 5dd box corners
    corners <- st_as_sf(data.frame(
                                    lon = c(min(df.window$x), max(df.window$x), max(df.window$x), min(df.window$x)),
                                    lat = c(min(df.window$y), min(df.window$y), max(df.window$y), max(df.window$y))
                                  ), coords = c("lon", "lat"), crs = 4326)
    
    
    # distance from each corner to track
    dists <- st_distance(corners, storm_track)
    closest_corner <- corners[which.min(dists), ]
    
    track_vertices <- st_coordinates(storm_track)   # matrix of lon/lat
    track_points <- st_as_sf(
      data.frame(track_vertices),
      coords = c("X", "Y"),
      crs = 4326
    )
    
    # distance track point -> closest corner
    d_track <- st_distance(track_points, closest_corner)
    
    # pick 2 closest points
    idx <- order(d_track)[1:2]
    closest_track_points <- track_points[idx, ]
    
    # final result = corner + 2 closest track points
    result <- list(
      corner = closest_corner,
      track_points = closest_track_points
      )
    
    # extract coordinates + attributes
    df_result <- cbind(
      st_drop_geometry(result$track_points),  # drops geometry, keeps fields
      st_coordinates(result$track_points)     # extracts lon/lat
    )
    
    pts_idx <- as.numeric(row.names(df_result))
    pos.1 <- seq(from=min(pts_idx),to=max(pts_idx),by=1)
    indic.1[pos.1] <- 1
    db.TC2$indic.buffer.TC[pos.1] <- 1 # Points artificially placed within the buffer
    
  }
  
  # Filter 1: There is no position within the 5dd buffer window of interest
  if(length(pos.1)==0 | all(indic.1==2)) next # no points within the box or only 2 points within it
        
  #Filter 2: Data length without missing value of required variables <= 1
  var.req <- cbind(db.TC1$LON, db.TC1$LAT, db.TC1$RMW, db.TC1$POCI, db.TC1$PRESS.MIN)
  indic.2 <- apply(var.req,1, function(x){ if(any(x==-99)){0}else{1} } ) # checking for No data time steps
  db.TC2 <- db.TC2 %>% add_column(indic.miss=indic.2) # 1 = data, 0 = missing data
  pos.2 <- which(indic.2!=0)
  if(length(intersect(pos.1, pos.2)) <= 1) next # if I have more than one point within the box and with data  = continue  
        
  # Calculate azimuth (it is used as direction here)
  dlon <- diff(db.TC2$LON)
  dlat <- diff(db.TC2$LAT)
  degree <- atan2(dlon,dlat) / pi * 180
  AZ <- ifelse(degree<0, degree +360, degree)
  AZ <- c(AZ, AZ[length(AZ)]) #assume that the TC keeps the direction at the last time step}
  db.TC2 <- db.TC2 %>% add_column(.after="PRESS.MIN", AZ=AZ)
        
  #grouping for continuous path
  pos.OK <- which(indic.1 == 1 & indic.2 == 1)
  sep <- which(diff(pos.OK)>1) #find the discrete location (where missing value exists or TC locations out of buffer window)
  n.group <- length(sep)+1
        
  group.contiuous <- array(NA,c(nrow(db.TC)))
  if(n.group==1 & all(db.TC2$indic.miss[pos.OK]==1)){
    group.contiuous[pos.OK] <- 1
  }else if(n.group>1){
    or.st <- 1
    gr.num <- 0
    for(ig in 1:n.group){
      if(ig!=n.group){
        pos.group <- pos.OK[or.st:sep[ig]]
        or.st = sep[ig] + 1  
      }else if(ig==n.group){
        pos.group <- pos.OK[or.st:length(pos.OK)]
      }
            
      if(length(pos.group) <= 1) next # I do not consider the TC event if the number of TC points is less than 2
        gr.num <- gr.num + 1
        group.contiuous[pos.group] <- gr.num
      }
  }
  db.TC2 <- db.TC2 %>% add_column(group.continuous=group.contiuous)
  db.TC2 <- db.TC2 %>% add_column(.before="NAME", POINT=1)
  db.TC2 <- db.TC2 %>% add_column(.after="POINT", "LAT.POINT" = ref.point$lon)
  db.TC2 <- db.TC2 %>% add_column(.after="POINT", "LON.POINT" = ref.point$lat)
  
############################################################
# (1.2) Calculate TC rainfall amounts using IPET model
############################################################
  # I divide the whole TC track into sub-groups if any required variable is missing
  n.groups <- length(unique(db.TC2$group.continuous[which(!is.na(db.TC2$group.continuous))]))
  if(n.groups == 0) next
  df.PRCP <- NULL
  for(igr in 1:n.groups){

    # I consider the TC period that the TC was located within the buffer window
    df.TC <- db.TC2 %>% filter(group.continuous == igr & indic.buffer.TC == 1)
    if(nrow(df.TC) < 2) next # If the number of TC points are less than 2, we cannot use temporal interpolation...
    
    n.times <- nrow(df.TC)
    n.times.hourly <- (n.times-1) * 6
    
    # I create an empty grid that will be used for IPET rainfall calculations
    prcp.accum <- matrix(0, n.lat, n.lon)
    prcp.hourly <- array(NA,c(n.lat, n.lon, n.times.hourly))
    prcp1 <- matrix(0, n.lat, n.lon)
    
    k = 0
    ihr = 0
    df.landfalling <- NULL
    count_igr <- count_igr + 1
    for(i in 2:n.times){
      
      ## for the current time step
      lon.TC1 <- df.TC$LON[i]
      lat.TC1 <- df.TC$LAT[i]
      rmw.TC1 <- df.TC$RMW[i] * 1.852  # radius of max winds (1knot = 1.852 km/h)
      dp.TC1 <- df.TC$POCI[i] - df.TC$PRESS.MIN[i] # the change in pressure between the outermost closed isobar and minimum central pressure
      press.min.TC1 <- df.TC$PRESS.MIN[i]
      date.TC1 <- as.POSIXct(paste0(df.TC$YEAR[i],"-",df.TC$MONTH[i],"-",df.TC$DAY[i]," ",df.TC$TIME[i],":00:00"), tz="GMT")
      
      ## for the previous time step
      lon.TC0 <- df.TC$LON[i-1]
      lat.TC0 <- df.TC$LAT[i-1]
      rmw.TC0 <- df.TC$RMW[i-1] * 1.852
      dp.TC0 <- df.TC$POCI[i-1] - df.TC$PRESS.MIN[i-1]
      press.min.TC0 <- df.TC$PRESS.MIN[i-1]
      az.TC0 <- df.TC$AZ[i-1] # azimuth
      date.TC0 <- as.POSIXct(paste0(df.TC$YEAR[i-1],"-",df.TC$MONTH[i-1],"-",df.TC$DAY[i-1]," ",df.TC$TIME[i-1],":00:00"), tz="GMT")
      
      ##########
      ## 1.2.1. Linear interpolation for temporal downscaling (6hr -> 20 min)
      ##########
      # Define the time step used for the linear interpolation between consecutive TC tracks
      timestep.min <- 20 # Here I use 20 min
      
      # Conduct interpolation in 20 min time scale
      elapsed.min <- (as.numeric(date.TC1) - as.numeric(date.TC0)) / 60 # minutes
      n.inter <- elapsed.min / timestep.min
      
      lon.TC.inter <- seq(lon.TC0, lon.TC1, length.out=n.inter+1)
      lat.TC.inter <- seq(lat.TC0, lat.TC1, length.out=n.inter+1)
      rmw.TC.inter <- seq(rmw.TC0, rmw.TC1, length.out=n.inter+1)
      dp.TC.inter <- seq(dp.TC0, dp.TC1, length.out=n.inter+1)
      press.min.TC.inter <- seq(press.min.TC0, press.min.TC1, length.out=n.inter+1)
      
      # Calculate translational velocity
      coords <- data.frame(lon=c(lon.TC1,lon.TC0),lat=c(lat.TC1,lat.TC0))
      dist.km <- geodist(coords,measure = "haversine")[1,2]/1000 # in km
      delta.t_obs <- as.numeric(difftime(date.TC1, date.TC0, units = "hours"))
      v.trans <- dist.km/6 #km/h
      v.trans.TC.inter <- rep(v.trans,18)
      
      # Calculate azimuth manually
      dlon <- diff(lon.TC.inter)
      dlat <- diff(lat.TC.inter)
      degree <- atan2(dlon,dlat) / pi * 180
      AZ.TC.inter <- ifelse(degree<0, degree +360, degree)
      AZ.TC.inter <- c(AZ.TC.inter, AZ.TC.inter[length(AZ.TC.inter)]) #assume that the TC keeps the direction at the last time step}
      
      # Identifying the landfall point (if there is one)
      indic.landfall <- sp::point.in.polygon(lon.TC.inter[2:19], lat.TC.inter[2:19], coast.pol$Lon, coast.pol$Lat)
      df.landfalling <- rbind(df.landfalling, data.frame(lon = lon.TC.inter[2:19], lat = lat.TC.inter[2:19], indic.lf = indic.landfall,
                                                         press.min = press.min.TC.inter[2:19],trans_vel = v.trans.TC.inter, AZ = AZ.TC.inter[2:19])
      )
    
      ##########################################################################
      # 1.2.2. IPET calculations
      ##########################################################################
      # convert degrees to radians
      lon.TC.inter_rad <- deg2rad(lon.TC.inter)
      lat.TC.inter_rad <- deg2rad(lat.TC.inter)
      lon.grids_rad <- deg2rad(lon.grids)
      lat.grids_rad <- deg2rad(lat.grids)
      
      # <Important>: Here I assume that the rainfall intensity calculated at 'itime'-th timestep lasts to 'itime+1'-th timestep.
      for(itime in 1:n.inter){
        k = k + 1
        #itime=1
        
        # Calculates the Euclidean radial distance between the lat/lon locations of the grid and the TC eye
        dlon.grids <- lon.grids_rad - lon.TC.inter_rad[itime]
        dlat.grids <- lat.grids_rad - lat.TC.inter_rad[itime]
        
        a <- sin(dlat.grids / 2.)^2. + cos(lat.TC.inter_rad[itime]) * cos(lat.grids_rad) * sin(dlon.grids / 2.)^2.
        gr <- 2.*asin(sqrt(a)) * 6371000. / 1000. # gr: radial distance (km) from the TC centre to each grid point
        
        ###############
        ## 1.2.2.1. Identify the grid cells that positioned to the right- and left-side of the TC direction
        ## The next three code chunks use the azimuth (i.e., TC direction) to isolate grid location to the right-side and left-side of the direction of travel
        ## and save two masks for these areas of the grid (named "left" and "right")
        ###############
        ### 1.2.2.2. Calculate the difference of degree between each grid point and the eye of TC
        ###        and transform from radian to degree
        lon.diff <- lon.grids - lon.TC.inter[itime]
        lat.diff <- lat.grids - lat.TC.inter[itime]
        angle.deg <- rad2deg( atan(lat.diff / lon.diff) ) # atan(y/x): the radian between the x-axis and the vector from the origin to (x,y)
        
        ### 1.2.2.3. Convert the coordinate squads (from Bearings to Azimuths)
        # Convert NE and SE quads 
        pos.2d <- which(lon.diff >= 0, arr.ind=TRUE)
        angle.deg[pos.2d] <- angle.deg[pos.2d]*-1.+90.
        # convert NW and SW quads
        pos.2d <- which(lon.diff < 0, arr.ind=TRUE)
        angle.deg[pos.2d] <- angle.deg[pos.2d]*-1.+270.
        
        ### 1.2.2.4. Isolate grid locations to the "right" and "left" of the direction of travel using the azimuth
        direction.path <- angle.deg - az.TC0
        pos.left <- which(direction.path > -180 & direction.path <= 0, arr.ind=TRUE)
        pos.right <- which(!(direction.path > -180 & direction.path <= 0), arr.ind=TRUE)
        
        ########################################################################
        ## 1.2.2.5 Calculate rainfall amount
        ## The next three code chunks where the IPET rainfall model is actually computed at each time interval
        ## IPET uses two different formulas based on the radius of maximum winds
        ## Grid locations to the right-side of the TC path receive a 1.5 x multiplier
        ########################################################################
        ### 1.2.2.6. Calculate mean rainfall intensity (mm / 20min) within RMW (radius of maximum winds)
        con1 <- which(gr <= rmw.TC.inter[itime], arr.ind=TRUE)
        inner_r_prcp <- matrix(0,n.lat,n.lon)
        inner_r_prcp[con1] <- (1.14 + 0.12 * dp.TC.inter[itime]) * (timestep.min/60.)
        inner_r_prcp[pos.right] <- inner_r_prcp[pos.right] * 1.5
        
        ### 1.2.2.7. Calculate mean rainfall intensity (mm / 20min) outside of RMW (radius of maximum winds)
        outer_r_prcp <- ( (1.14 + 0.12*dp.TC.inter[itime]) * exp(-0.3*((gr - rmw.TC.inter[itime]) / rmw.TC.inter[itime])) )*(timestep.min/60.)
        outer_r_prcp[con1] <- 0
        outer_r_prcp[pos.right] <- outer_r_prcp[pos.right] * 1.5
        
        ### 1.2.2.8. Obtain accumulated rainfall amounts
        # hourly rainfall amounts
        prcp1 <- prcp1 + inner_r_prcp + outer_r_prcp
        if(k%%3 == 0){
          ihr <- ihr + 1
          prcp1[cells_sea.idx] <- 0 
          prcp.hourly[,,ihr] <- prcp1
          prcp1 <- matrix(0,n.lat,n.lon)
        }
        # rainfall amounts for the whole TC period (within rain buffer window)
        prcp.accum <-  prcp.accum + inner_r_prcp + outer_r_prcp
      }# end interpolation loop
    }# end of time step loop
    ################################
    ## 1.3 Reformatting the results
    ################################
    # create data.frame of IPET accumulated rainfall amounts
    prcp.accum[cells_sea.idx] <- 0
    df.prcp.accum <- as.data.frame(cbind(c(lon.grids), c(lat.grids), c(prcp.accum)))
    colnames(df.prcp.accum) <- c("lon","lat","PRCP.accum")
    df.prcp.accum$lon <- round(df.prcp.accum$lon,3)
    df.prcp.accum$lat <- round(df.prcp.accum$lat,3)
    
    # re-order the grid cells
    if(iTC==1){
      pos.reorder <- array(NA,n.grid)
      for(igrid in 1:n.grid){
        if(igrid%%5000 == 0) print(paste0(igrid,"/",n.grid))
        pos.reorder[igrid] <- which(df.prcp.accum$lon==df.grid.xy[igrid,]$x & df.prcp.accum$lat==df.grid.xy[igrid,]$y)
      }  
    }
    
    prcp.accum.t <- list()
    prcp.accum.t[[1]] <- data.frame(lon=df.grid.xy$x, lat=df.grid.xy$y, PRCP.accum=df.prcp.accum$PRCP.accum[pos.reorder])
    date.st.POSIX <- as.POSIXct(paste0(df.TC$YEAR[1],"-",df.TC$MONTH[1],"-",df.TC$DAY[1]," ",df.TC$TIME[1],":00:00"), tz="GMT")
    date.en.POSIX <- as.POSIXct(paste0(df.TC$YEAR[n.times],"-",df.TC$MONTH[n.times],"-",df.TC$DAY[n.times]," ",df.TC$TIME[n.times],":00:00"), tz="GMT")
    lag.t <- as.numeric(difftime(date.en.POSIX, date.st.POSIX, units="hours"))
    
    ########################################################################################################################################################
    # I assume that IPET rainfall intensity calculated at i-th time lasts to i+1 -th time.
    # Therefore, the amount of hourly rainfall at 01:00:00 is calculated by summing up the IPET rainfalls calculated at 00:00:00, 00:20:00, and 00:40:00
    ########################################################################################################################################################
    prcp.accum.t[[2]] <- seq(date.st.POSIX, date.en.POSIX, by="hours")[2:(lag.t+1)]
    
    # I also save hourly prcp
    if( dim(prcp.hourly)[3] != length(prcp.accum.t[[2]]) ) print( "check hourly PRCP!" )
    
    prcp.hourly.all <- NULL
    for(ihr in 1:n.times.hourly){
      prcp.hourly.all <- cbind(prcp.hourly.all, c(prcp.hourly[,,ihr])[pos.reorder])
    }
    df.prcp.hourly.all <- data.frame(lon=df.grid.xy$x, lat=df.grid.xy$y, prcp.hourly.all)
    colnames(df.prcp.hourly.all) <- c("lon","lat",paste0("hr",c(1:n.times.hourly)))
    
    prcp.hourly.t <- list()
    prcp.hourly.t[[1]] <- df.prcp.hourly.all
    prcp.hourly.t[[2]] <- seq(date.st.POSIX, date.en.POSIX, by="hours")[2:(lag.t+1)]
    
    #####################################################
    # 1.4. Populating data frame with TC info
    #####################################################
    pos.landfall <- which(df.landfalling$indic.lf == 1)[1] #first landfalling time step
    check_NAs <- which(is.na(pos.landfall)==TRUE)
    
    if(length(check_NAs)!=0){ #cleaning up landfall points by removing all NAs
      pos.landfall <- pos.landfall[-c(check_NAs)]
    }
    
    if(length(pos.landfall)!=0){
      
      df.TC.char[count_igr,]$TC.order <- count_igr
      df.TC.char[count_igr,]$TC.year <- TC.year
      df.TC.char[count_igr,]$TC.name <- TC.name
      df.TC.char[count_igr,]$TC.group <- igr
      df.TC.char[count_igr,]$press.min <- df.landfalling$press.min[pos.landfall]
      df.TC.char[count_igr,]$v.tran <- df.landfalling$trans_vel[pos.landfall]
      df.TC.char[count_igr,]$AZ <- df.landfalling$AZ[pos.landfall]
      
      ###############################################################################################
      # Adjustment to compute the overall BIAS - Total rainfall has to be computed based on 3dd box
      ###############################################################################################
      # 3dd bounding box
      win.crop = 3
      lon.min_crop <- ref.point$lon - win.crop/2
      lon.max_crop <- ref.point$lon + win.crop/2
      lat.min_crop <- ref.point$lat - win.crop/2
      lat.max_crop <- ref.point$lat + win.crop/2
      
      # set to zero the values for PRCP accumulated
      df.prcp_bias <- prcp.accum.t[[1]]
      
      # verify the ones within and outside the new crop bounding box
      cells_bb <- which(df.prcp_bias$lon >= lon.min_crop & df.prcp_bias$lon <= lon.max_crop &
                          df.prcp_bias$lat >= lat.min_crop & df.prcp_bias$lat <= lat.max_crop)
      
      # Computes the total rainfall within the 3dd box to be used in overall BIAS calculations
      tot.rain_crop <- sum(df.prcp_bias$PRCP.accum[cells_bb])
      
      ##########################################################################
      # Populating the TC characteristics matrix
      df.TC.char[count_igr,]$rainfall.total.IPET <- tot.rain_crop # in mm for the whole 3dd bounding box domain
      
    } else { # if I don't have landfall, the values are equal to average of the available data set within the bounding box
      
      df.TC.char[count_igr,]$TC.order <- count_igr
      df.TC.char[count_igr,]$TC.year <- TC.year
      df.TC.char[count_igr,]$TC.name <- TC.name
      df.TC.char[count_igr,]$TC.group <- igr
      df.TC.char[count_igr,]$press.min <- round(mean(df.TC$PRESS.MIN,na.rm=TRUE),2)
      df.TC.char[count_igr,]$AZ <- round(mean(df.TC$AZ,na.rm=TRUE),2)
      
      ###############################################################################################
      # Adjustment to compute the overall BIAS - Total rainfall has to be computed based on 3dd box
      ###############################################################################################
      # 3dd bounding box
      win.crop = 3
      lon.min_crop <- ref.point$lon - win.crop/2
      lon.max_crop <- ref.point$lon + win.crop/2
      lat.min_crop <- ref.point$lat - win.crop/2
      lat.max_crop <- ref.point$lat + win.crop/2
      
      # set to zero the values for PRCP accumulated
      df.prcp_bias <- prcp.accum.t[[1]]
      
      # verify the ones within and outside the new crop bounding box
      cells_bb <- which(df.prcp_bias$lon >= lon.min_crop & df.prcp_bias$lon <= lon.max_crop &
                          df.prcp_bias$lat >= lat.min_crop & df.prcp_bias$lat <= lat.max_crop)
      
      # Computes the total rainfall within the 3dd box to be used in overall BIAS calculations
      tot.rain_crop <- sum(df.prcp_bias$PRCP.accum[cells_bb])
      
      ##########################################################################
      # Populating the TC characteristics matrix
      df.TC.char[count_igr,]$rainfall.total.IPET <- tot.rain_crop # in mm for the whole 3dd bounding box domain
      
      # estimating average v. trans for "observational" track
      coords <- data.frame(lon = df.TC$LON,lat = df.TC$LAT)
      ## Compute Haversine distances (in meters) between all pairs
      dist_matrix <- geodist(coords, measure = "haversine")/1000  # Convert to km
      ## time steps 
      time <- as.POSIXct(paste0(df.TC$YEAR,"-",df.TC$MONTH,"-",df.TC$DAY," ",df.TC$TIME,":00:00"),format= "%Y-%m-%d %H:%M:%S", tz="UTC")
      t.step_obs <- as.numeric(diff(time))
      ## vtrans calculation
      row_idx.vt <- seq(1,(nrow(coords)-1),1)
      col_idx.vt <- seq(2,nrow(coords),1)
      pairs_idx <- cbind(row_idx.vt,col_idx.vt)
      v.trans <- dist_matrix[pairs_idx]/t.step_obs # in km/k
      df.TC.char[count_igr,]$v.tran <- mean(v.trans)
    }       
    
    ################################################################
    # (2) Bias correction  
    ################################################################
    # (2.1) Overall BIAS ("BIAS.1") - Gamma Model (GA) 
    # mu: log10 storm total rainfall and translational velocity
    # sigma: log10 storm total rainfall and direction
    #################################################################
    # (2.1.1) Parameter estimation
    prob <- 0.50
    mu_par <- exp(-4.75 + 0.763*log10(df.TC.char$rainfall.total.IPET[count_igr]) + 0.025*df.TC.char$v.tran[count_igr])
    sigma_par <- exp(-9.50+1.43*log10(df.TC.char$rainfall.total.IPET[count_igr])+0.009*df.TC.char$AZ[count_igr])
    shape.GA <- 1/(sigma_par^2)
    scale.GA <- (sigma_par^2)*(mu_par)
    
    # (2.1.2) Bias estimation
    BIAS.overall <- stats:: qgamma(prob, shape = shape.GA, scale = scale.GA) # overall BIAS model - estimates produced for a single TC event
    
    # (2.1.3) Apply overall BIAS model to raw IPET
    # total rainfall
    PRCP.IPET <- (prcp.accum.t[[1]])[,3] # pixel-based accumulated rainfall during a TC
    PRCP.BC1 <- PRCP.IPET * BIAS.overall # overall BIAS correction
    
    # hourly rainfall
    nhr <- length(prcp.hourly.t[[2]]) 
    PRCP.BC1_hr <- prcp.hourly.t[[1]][,2+c(1:nhr)] * BIAS.overall
   
    ################################################################
    # (2.2) Rain dependent BIAS ("BIAS.2")
    # Power function: BIAS2 = a*(BIAS1)^1.173 
    #################################################################
    # (2.2.1) model parameters
    coeff.a <- 0.6035065
    coeff.b <- 1.1734439
    
    # (2.2.1) apply conditional BIAS model to overall BIAS-corrected IPET
    # total rainfall
    PRCP.BC2 <- coeff.a * (PRCP.BC1)^coeff.b
    
    # hourly rainfall
    ## Obtain the total amount of TC rainfall for the whole period (hours)
    total.rainfall <- apply(PRCP.BC1_hr,1,sum)
    ## calculate hourly weights
    weight.hr <- PRCP.BC1_hr / total.rainfall
    NA_cells.idx <- which(is.na(weight.hr)==TRUE,arr.ind = TRUE) # row and cols of ocean cells
    weight.hr[NA_cells.idx] = 0 # bc of the zeros in the ocean, I have to correct here
    ## disaggregate the bias-corrected total rainfall amount using hourly weights
    PRCP.BC2_hr <-  PRCP.BC2 * weight.hr
    
    ##################################################################
    # (2.3) Create a data frame with the lat/lon, PRCP, BC1, BC2
    ##################################################################
    df.PRCP <- prcp.accum.t[[1]] %>% add_column(prcp.bc.overall=PRCP.BC1) # adding lat/lon, IPET accumulated, BC1
    df.PRCP <- df.PRCP %>% add_column(prcp.bc.conditional=PRCP.BC2) # adding BC2
    
    df.PRCP_hr <- cbind(prcp.hourly.t[[1]]$lon, prcp.hourly.t[[1]]$lat, PRCP.BC2_hr)
    colnames(df.PRCP_hr) <- c("lon", "lat", colnames(PRCP.BC2_hr))
    
    #################################################################
    ## (3) apply generated error fields
    #################################################################
    # set.seed(52246) #If you wanna to have the same results for the sample function, remove the comment
    # load generated spatial error fields
    df.simfield.mix <- readRDS("RandomFields/GenSamples.rds")
    
    # Inputs and variables
    number.sim <- c(1:nsim)
    order.sim <- sample(number.sim, gg.nsim, replace=F) # Randomly select 3 simulation results
    order.sim.t[count_igr,] <- order.sim
    
    df.fin <- list()
    n.gen <- 0
    for(isim in order.sim){
      
      print(isim)
      
      df.simfield.mix.select <- df.simfield.mix %>% dplyr::select("lon","lat",paste0("sim",isim))
      colnames(df.simfield.mix.select) <- c("lon","lat","rand.comp")
      
      # total rainfall
      PRCP.gen <- PRCP.BC2 * exp(df.simfield.mix.select$rand.comp)
      df.PRCP <- df.PRCP %>% add_column(prcp.gen=PRCP.gen)
      
      # hourly rainfall
      n.gen <- n.gen + 1 
      PRCP.gen_hr <- df.PRCP_hr[,2+c(1:nhr)] * exp(df.simfield.mix.select$rand.comp)
      df.fin_hr <- cbind(df.PRCP$lon, df.PRCP$lat,PRCP.gen_hr)
      colnames(df.fin_hr) <- c("lon", "lat", colnames(PRCP.gen_hr))
      df.fin_hr[NA_cells.idx[,1],c(3:ncol(df.fin_hr))] <- NA # correcting for the ocean cells - save
      df.fin[[n.gen]] <-  df.fin_hr
      
      ##########################################
      # Create netcdf files for hourly values
      ##########################################
      #saving path
      save_path <- paste0("Results_Rainfall_Fields/nc_files/RFF_",n.gen,"_",TC.name,TC.year,"_",igr,"grp.nc")
      
      lon.4nc <- unique(df.fin_hr$lon)
      lat.4nc <- unique(df.fin_hr$lat)
      time.4nc <- as.numeric(prcp.hourly.t[[2]])
      
      nlon <- length(lon.4nc)
      nlat <- length(lat.4nc)
      ntime <- length(time.4nc)
      
      # create arrays and put values
      precip_array <- array(NA, dim=c(nlon,nlat,ntime))
      for(itime in 1:ntime){
        vals <- as.matrix(pivot_wider(df.fin_hr[,c(1,2,(2+itime))], names_from = lat, values_from = paste0("hr",itime)))[,-1]
        precip_array[,,itime] <- vals
      }
      
      # define dimensions
      londim <- ncdim_def("lon","decimal degrees east", as.double(lon.4nc)) 
      latdim <- ncdim_def("lat","decimal degrees north", as.double(lat.4nc)) 
      timedim <- ncdim_def("time","seconds since 1970-01-01 00:00:00 GMT", as.double(time.4nc))
      
      # define variables
      ## PRCP 
      fillvalue <- NA
      dlname <- "Precip"
      precip_def <- ncvar_def("PRCP", "mm", list(londim,latdim,timedim), fillvalue, dlname, prec="single")
      
      # create netCDF file and put arrays
      ncfname <- save_path
      ncout <- nc_create(ncfname,list(precip_def), force_v4=TRUE)
      
      # put variables
      ncvar_put(ncout,precip_def,precip_array)
      
      # put additional attributes into dimension and data variables
      ncatt_put(ncout,"lon","axis","X") #,verbose=FALSE) #,definemode=FALSE)
      ncatt_put(ncout,"lat","axis","Y")
      ncatt_put(ncout,"time","axis","T")
      
      # Add CRS information as global attributes
      ncatt_put(ncout, 0, "crs", "EPSG:4326")
      ncatt_put(ncout, 0, "spatial_ref", "GEOGCS['WGS 84',DATUM['WGS_1984',SPHEROID['WGS 84',6378137,298.257223563]],PRIMEM['Greenwich',0],UNIT['degree',0.0174532925199433]]")
      
      print(ncout)

      # close the file, writing data to disk
      nc_close(ncout)
      
    }
    # avoids that for the next TC, we select the same random component
    number.sim <- number.sim[-which(number.sim %in% order.sim)] 
    
    # total rainfall 
    df.PRCP[NA_cells.idx[,1],c(3:ncol(df.PRCP))] <- NA # correcting for the ocean cells - save
    TCrain.sim[[count_igr]] <- df.PRCP
    
    # hourly rainfall
    TCrain.sim_hr[[count_igr]] <- df.fin
    
  } # end of igr group for a TC
}# end TC loop

################################################################################
# END
################################################################################