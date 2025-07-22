
import os
import matplotlib.pyplot as plt
import warnings
import pandas as pd
import h5py
import numpy as np
import matplotlib.dates as mdates
from pyproj import CRS
import geopandas as gpd
import tqdm
from shapely.geometry import Point, Polygon, mapping, box
import time
from datetime import datetime
import re
import contextily as ctx
import plotly.graph_objects as go
import itables
import difflib
from IPython.display import display, HTML
from itables import init_notebook_mode, show
import plotly.express as px
from IPython.display import display
from plotly.subplots import make_subplots

itables.options.showIndex = True
warnings.filterwarnings("ignore")





# ### Define functions

# In[4]:


def clean_attr_value(value):
    # If it's a NumPy array with one element, extract the scalar
    if isinstance(value, np.ndarray) and value.size == 1:
        value = value.item()

    # If it's a byte string, decode it
    if isinstance(value, bytes):
        value = value.decode('utf-8')

    return value

def decode_time(raw_time):
    """
    decode time in hdf file.
    """
    times = [datetime.strptime(str(int(t)), '%Y%m%d%H%M') for t in raw_time]
    return times


def find_matching_storm_name(partial_name, storm_list):
    """
    Finds the first matching storm name from a list using a wildcard pattern.
    """
    pattern = re.compile(partial_name.replace('*', '.*'))
    matches = [col for col in storm_list if pattern.match(col)]
    return matches[0] if matches else None


def load_data(plan_file):
    return h5py.File(plan_file, 'r')

def get_model_info(data):
    """
    load name of the 2D perimeter in the model.
    """
    model_info_name = data['/Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/2D Flow Areas/'].keys()
    for mdl_inf_nm in model_info_name:
        return mdl_inf_nm

def plot_ts(df_wse_model1,df_wse_model2,check_cell_id):
     #check_cell_id = 357608
     plt.figure()
     df_wse_model1[check_cell_id].plot(c='k',label='windows')
     df_wse_model2[check_cell_id].plot(c='r',label='linux')
     plt.legend()



def extract_geometry(data, mdl_inf_nm):
    """
    extract model geometry variables.
    """
    geo = data.get('Geometry')
    model_units = geo.attrs['SI Units'].decode("utf-8")
    projcs_string = data.attrs['Projection'].decode("utf-8")
    model_prj_epsg = CRS.from_wkt(projcs_string)
    epsg_code = model_prj_epsg.to_epsg()
    geom_xy = geo.get('2D Flow Areas').get(mdl_inf_nm).get('Cells Center Coordinate')[:, :]
    cell_surface_area = geo.get('2D Flow Areas').get(mdl_inf_nm).get('Cells Surface Area')[:]

    x, y = geom_xy[:, 0], geom_xy[:, 1]
    return x, y,model_prj_epsg, epsg_code, cell_surface_area


def create_geodataframe(x, y, epsg_code,cell_surface_area):
    """
    converts model attributes into a geodataframe.
    """
    model_cells = pd.DataFrame({'x': x, 'y': y})
    model_gdf = gpd.GeoDataFrame(model_cells.index, crs=epsg_code, geometry=gpd.points_from_xy(x=model_cells.x, y=model_cells.y))
    model_gdf.columns = ['CellNum', 'geometry'] 
    # Adding Cell surface area to compute cell average size
    model_gdf['surface_area'] = cell_surface_area
    model_gdf['surface_area'] = model_gdf['surface_area'].astype(float)

    return model_gdf

def create_domain_polygon(x, y):
    """
    converts min max coordinates of mesh to a bounding box object.
    """
    coords = [(x.min(), y.max()), (x.max(), y.max()), (x.max(), y.min()), (x.min(), y.min())]
    ras_domain_poly1 = Polygon(coords)
    ras_domain_poly = Polygon(ras_domain_poly1.buffer(1.0 * 7500))
    return ras_domain_poly

def extract_boundary_conditions(data, mdl_inf_nm):
    """
    extracts boundary conditions
    """
    Bnd_cond = data[f'/Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/2D Flow Areas/{mdl_inf_nm}/Boundary Conditions']
    boundary_conditions = {kk: Bnd_cond[kk][:] for kk in Bnd_cond.keys()}
    return boundary_conditions

def extract_results_summary(data):
    """
    extract_results_summary
    """
    try:
        Results_summary = data.get('Results').get('Summary').get('Compute Messages (text)')
        Results_text_data = Results_summary[0].decode('utf-8')
        return Results_text_data
    except:
        return 'Result summary not extracted'



def extract_result_field(data, mdl_inf_nm, field_name):
    """
    extract requested variables of model outputs in the results hdf block
    """ 
    try:
        # Define base paths
        base_path = f'/Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/2D Flow Areas/{mdl_inf_nm}'
        time_path = '/Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series'

        # Extract the field data
        field_data = data[base_path][field_name][:, :]
        df_out = pd.DataFrame(field_data)

        # Extract and parse timestamps
        timesteps = data[time_path]['Time Date Stamp'][:]
        timestamps = pd.to_datetime([t.decode('utf-8') for t in timesteps], format="%d%b%Y %H:%M:%S")
        df_out.index = timestamps

        return df_out

    except Exception as e:
        print(f"!!! ERROR !!! Output not loaded properly: {e}")
        return None



def extract_event_field(data, field_name):
    """
    extract requested variables of model input forcing in the event condition hdf block
    """ 

    base_path = 'Event Conditions'

    if field_name == 'Wind':
        cell_wgts = data[f'{base_path}/Meteorology/Wind/2D Flow Areas/PERIMTER1/Cell Weights'][:]
        ts = data[f'{base_path}/Meteorology/Wind/Timestamp'][:]
        vx = data[f'{base_path}/Meteorology/Wind/VX'][:]
        vy = data[f'{base_path}/Meteorology/Wind/VY'][:]
        return cell_wgts, ts, vx, vy

    elif field_name == 'Air Density':
        air_value = data[f'{base_path}/Meteorology/Air Density/Values'][:]
        return air_value

    elif field_name == 'Boundary Conditions':
        unsteady_path = data.get(base_path).get('Unsteady').get('Boundary Conditions')
        bc_name_nd = list(unsteady_path.get('Normal Depths').keys())[0]
        nd_value = unsteady_path.get('Normal Depths').get(bc_name_nd)[:]

        bc_name_stage = list(unsteady_path.get('Stage Hydrographs').keys())[0]
        stage_value = unsteady_path.get('Stage Hydrographs').get(bc_name_stage)[:]
        stage_bc_table = pd.DataFrame(stage_value)

        return nd_value, stage_bc_table

    elif field_name == 'Initial Conditions':
        ic_path = data.get(base_path).get('Unsteady').get('Initial Conditions')
        ic_vals = ic_path.get('IC Point Elevations')[:]
        ic_position = ic_path.get('IC Point Fixed')[:]
        ic_names = ic_path.get('IC Point Names')[:]

        ic_table = pd.DataFrame(ic_names.astype(str))
        ic_table['Elevation'] = ic_vals.astype(float).round(2)
        ic_table['Fixed'] = ic_position
        ic_table = ic_table.set_index(0)
        ic_table.index.names = ['Name']

        return ic_table

    else:
        print(f"Field '{field_name}' is not defined.")
        return None



def list_hdf_result_fields(data, mdl_inf_nm):
   available_fields_hdf = data[f'/Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/2D Flow Areas/{mdl_inf_nm}'].keys()
   return  list(available_fields_hdf)

def list_hdf_eventcondition_fields(data, mdl_inf_nm):
   available_fields_met = list(data['Event Conditions/Meteorology'].keys())
   available_fields_unsteady = list(data['Event Conditions/Unsteady'].keys())

   print(f'Available Meteorology fields in hdf file:\n{available_fields_met}')
   print(f'Available Unsteady fields in hdf file:\n{available_fields_unsteady}')

   return None

def extract_compute_log(lines):
    # Initialize variables
    extracting = False
    selected_lines = []

    # Loop through the lines and extract the desired section
    for line in lines:
        if start_marker in line:
            extracting = True
        if extracting:
            selected_lines.append(line)
        if end_marker in line:
            break

    # Display the extracted lines
    extracted_text = ''.join(selected_lines)
    #print(extracted_text)
    return extracted_text


def extract_error(text):
    # Extract the values using regular expressions
    acre_feet_match = re.search(r'Overall Volume Accounting Error in Acre Feet:\s+([\d.]+)', text)
    percentage_match = re.search(r'Overall Volume Accounting Error as percentage:\s+([\d.]+)', text)

    # Store the values in variables
    acre_feet_error = float(acre_feet_match.group(1)) if acre_feet_match else None
    percentage_error = float(percentage_match.group(1)) if percentage_match else None

    # Output the extracted values
    acre_feet_error, percentage_error
    return acre_feet_error, percentage_error


def get_compute_dataframe(lines):
    data = []
    for line in lines:
        match = re.match(r'(\d{2}[A-Z]{3}\d{4} \d{2}:\d{2}:\d{2})\s+PERIMTER1\tCell #\t\s+(\d+)\t\s+([\d.]+)\t\s+([\d.]+)\t(\d+)', line)
        if match:
            dt_str, cell, wsel, error, iterations = match.groups()
            dt = datetime.strptime(dt_str, '%d%b%Y %H:%M:%S')
            data.append([dt, int(cell), float(wsel), float(error), int(iterations)])

    # Create DataFrame
    df = pd.DataFrame(data, columns=['Datetime', 'Cell', 'WSEL', 'ERROR', 'ITERATIONS'])
    df = df.set_index('Datetime')
    df.index = pd.to_datetime(df.index)


    return df



def read_solver_cores_warmups (file_path,stormID):
    with open(file_path, 'r') as file:
        content = file.read()

        if 'HDF_ERROR trying to close HDF output file' in content:
            # model didnot run possibly
            df= pd.DataFrame([0]*14)
            df.index = df_major.index
            df.loc['StormID',:] = [stormID]
            df.loc['Status',:] = ['HDF Error']

            df_major[stormid] = df


        content_list = content.split('\n') 
        # find info from start
        content_start =  content_list[:25]
        data_lines = [line.strip() for line in content_start if line.strip() and not line.strip().startswith("PROGRESS=")]

        # Initialize dictionary to store extracted values       
        extracted_data = {}

        timesteps = None
        solver_cores = None

        for line in data_lines:
            if 'Number of warm up time steps' in line:
                timesteps = int(line.split(':')[-1].strip())
            elif '2D number of Solver Cores' in line:
                solver_cores = int(line.split(':')[-1].strip())
        # fill info
        extracted_data['StormID'] = stormID
        extracted_data['Solver_cores'] = solver_cores
        extracted_data['Warm up time steps'] = timesteps

        return extracted_data


def h5tree_view(file, include_keys=None):
    """Display selected HDF5 groups in tree-like format.

    Parameters
    ----------
    file : h5py.File
        Opened HDF5 file.
    include_keys : list or None
        List of top-level keys to include (e.g., ['Results', 'Outputs']).
        If None, shows all.
    """
    import h5py
    assert isinstance(file, h5py._hl.files.File)

    def view_h5attributes(obj, depth=0):
        atts = obj.attrs
        deep = "│   " * depth
        for i, k in enumerate(atts.keys()):
            d = deep + ("└──" if i == len(atts)-1 else "├──")
            try:
                if k in ['Faces','Times']:
                    continue
                else:
                    print(d, f'🏷️{k} = `{atts[k].decode("utf-8")}`')
            except (UnicodeDecodeError, AttributeError):
                if k in ['Faces','Times']:
                    continue
                else:
                    print(d, f'🏷️{k} = `{atts[k]}`')

    def view_h5object(obj, depth=0):
        name = obj.name.split("/")[-1]
        deep = "│   " * depth + "├──"
        if isinstance(obj, h5py.Group):
            print(deep, f"📁{name}")
            view_h5attributes(obj, depth=depth + 1)
            for k in obj:
                view_h5object(obj[k], depth=depth + 1)
        else:
            print(deep, f"🔢{name} ⚙️{obj.shape}{obj.dtype}")
            view_h5attributes(obj, depth=depth + 1)

    print(".", file.filename)
    keys_to_view = include_keys if include_keys else list(file.keys())
    for k in keys_to_view:
        if k in file:
            view_h5object(file[k], depth=0)
        else:
            print(f"❌ Key '{k}' not found in file.")



def extract_IC_gdf(data):
    ic_ele = data['Event Conditions/Unsteady/Initial Conditions/IC Point Elevations'][:]
    ic_fxd = data['Event Conditions/Unsteady/Initial Conditions/IC Point Fixed'][:]
    ic_name= data['Event Conditions/Unsteady/Initial Conditions/IC Point Names'][:]
    ic_xy  = data['Geometry/IC Points/Points'][:]
    ic_attrs  = data['Geometry/IC Points/Attributes'][:]
    
    # print(ic_ele,ic_fxd,ic_name,ic_xy,ic_attrs)
    
    
    # Create a GeoDataFrame
    ic_geometry = [Point(xy) for xy in ic_xy]
    ic_gdf = gpd.GeoDataFrame({
        'name': [name.decode().strip() for name in ic_name],
        'elevation': ic_ele,
        'fixed': ic_fxd,
        'name': [attr[0].decode().strip() for attr in ic_attrs],
        '2D area': [attr[1].decode().strip() for attr in ic_attrs],
        'cell ID': [attr[2] for attr in ic_attrs]
    }, geometry=ic_geometry)

    return ic_gdf



    
substrings_to_remove = ['PROGRESS=', 'SIMTIME=', 'ABSDATE=', 'ABSTIME=', 'ITER2D=']
