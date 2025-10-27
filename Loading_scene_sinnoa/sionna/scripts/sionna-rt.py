import os # Configure which GPU
if os.getenv("CUDA_VISIBLE_DEVICES") is None:
    gpu_num = 0 # Use "" to use the CPU
    os.environ["CUDA_VISIBLE_DEVICES"] = f"{gpu_num}"
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Import or install Sionna
try:
    import sionna.phy
    import sionna.rt
except ImportError as e:
    import sys
    if 'google.colab' in sys.modules:
       # Install Sionna in Google Colab
       print("Installing Sionna and restarting the runtime. Please run the cell again.")
       os.system("pip install sionna")
       os.kill(os.getpid(), 5)
    else:
       raise e

# Configure the notebook to use only a single GPU and allocate only as much memory as needed
# For more details, see https://www.tensorflow.org/guide/gpu
import tensorflow as tf
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        tf.config.experimental.set_memory_growth(gpus[0], True)
    except RuntimeError as e:
        print(e)

# Avoid warnings from TensorFlow
tf.get_logger().setLevel('ERROR')

import numpy as np

# For link-level simulations
from sionna.phy.channel import OFDMChannel, CIRDataset
from sionna.phy.nr import PUSCHConfig, PUSCHTransmitter, PUSCHReceiver
from sionna.phy.utils import ebnodb2no, PlotBER
from sionna.phy.ofdm import KBestDetector, LinearDetector
from sionna.phy.mimo import StreamManagement

# Import Sionna RT components
from sionna.rt import load_scene, Camera, Transmitter, Receiver, PlanarArray,\
                      PathSolver, RadioMapSolver

no_preview = False # Toggle to False to use the preview widget
                  # instead of rendering for scene visualization

# System parameters
subcarrier_spacing = 30e3 # Hz
num_time_steps = 14 # Total number of ofdm symbols per slot
carrier_frequency = 3.5e9 # Hz


num_tx = 2 # Number of users
num_rx = 1 # Only one receiver considered
num_tx_ant = 1 # Each user has 4 antennas
num_rx_ant = 2 # The receiver is equipped with 16 antennas

# batch_size for CIR generation
# batch_size_cir = 1000
batch_size_cir = 6

# Load an integrated scene.
# You can try other scenes, such as `sionna.rt.scene.etoile`. Note that this would require
# updating the position of the transmitter (see below in this cell).
# scene = load_scene(sionna.rt.scene.munich)
scene =  load_scene("../blender_xml/nycu_right/nycu_right.xml")
# scene.preview()

# Transmitter (=basestation) has an antenna pattern from 3GPP 38.901
scene.tx_array = PlanarArray(num_rows=1,
                             num_cols=num_rx_ant//2, # We want to transmitter to be equiped with 2 antennas
                             vertical_spacing=0.5,
                             horizontal_spacing=0.5,
                             pattern="tr38901",
                             polarization="cross")

# Create transmitter
tx1 = Transmitter(name="tx1",
                 position=[30, 20, 50],
                 look_at=[30,0,10], # optional, defines view direction
                 power_dbm=23,
                 display_radius=3.) # optinal, radius of the sphere for visualizing the device

tx2 = Transmitter(name="tx2",
                 position=[30,46,22],
                 look_at=[30,0,10], # optional, defines view direction
                 power_dbm=23,
                 display_radius=3.) # optinal, radius of the sphere for visualizing the device

# scene.preview()

scene.add(tx1)
scene.add(tx2)

# Create new camera
bird_cam = Camera(position=[0,80,500], orientation=np.array([0,np.pi/2,-np.pi/2]))

# max_depth = 5
max_depth = 12

# Radio map solver
rm_solver = RadioMapSolver()

# Compute the radio map
rm = rm_solver(scene,
               max_depth=12,
               cell_size=(1., 1.),
               samples_per_tx=10**7)

if no_preview:
    # Render an image
    scene.render(camera=bird_cam,
                 radio_map=rm,
                 rm_vmin=-110,
                 clip_at=12.); # Clip the scene at rendering for visualizing the refracted field
else:
    # Show preview
    scene.preview(radio_map=rm,
                  rm_vmin=-110,
                  clip_at=40.); # Clip the scene at rendering for visualizing the refracted field