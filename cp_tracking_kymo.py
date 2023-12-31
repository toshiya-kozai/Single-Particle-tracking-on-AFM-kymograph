# needed imports
import argparse
import yaml
import numpy as np
import pandas as pd
import skimage.io as skio
from scipy.signal import iirfilter, filtfilt, find_peaks
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description="Run particle tracking on AFM kymograph.")
# expect yaml parameter file
parser.add_argument('-p',
                    dest='prm',
                    required=True,
                    type=argparse.FileType('r'),
                    help="provide a parameter file in yaml format.")

args = parser.parse_args()
imgp = yaml.safe_load(args.prm)

inputdir = imgp['filenames']['data_dir']
data_name = imgp['filenames']['data_name']

pixel_size = imgp['parameters']['pixel_size']
distance_from_center = imgp['parameters']['distance_from_center']
top_pixels = imgp['parameters']['top_pixels']
bottom_pixels = imgp['parameters']['bottom_pixels']
border = imgp['parameters']['border']
cutoff_length = imgp['parameters']['cutoff_length']

def butter_lowpass_filter(signal, cutoff, length, order = 4):
    b, a = iirfilter(order, Wn=cutoff, fs=length, btype="low", ftype="butter")
    # print(b, a, sep="\n")
    filtered_signal = filtfilt(b, a, signal)
    return filtered_signal

def track_cp_kymo(inputdir, data_name, pixel_size, pixels, bottom_pixels, border, distance_from_center, cutoff_length):
  
    kymo = skio.imread(inputdir + "/" + data_name + ".tiff", plugin="tifffile")
    nrows, nlines = kymo.shape

    # for lowpass filter
    length = 1/pixel_size
    cutoff = 1/cutoff_length

    # in the fast-scan axis
    lowpass_filtered_list = np.zeros((nrows, nlines), dtype=np.float32)
    for iline in range(nlines):
        filtered_signal = butter_lowpass_filter(kymo[:, iline], cutoff, length, order = 4)
        lowpass_filtered_list[:, iline] = filtered_signal

    y = []
    for iline in range(nlines):

        local_maxima, _ = find_peaks(lowpass_filtered_list[pixels:(nrows - bottom_pixels), iline], height = border)
        print("detected local maxima positions:", local_maxima)
      
        if len(local_maxima) > 1:
            max_list = []
          
            for i in range(len(local_maxima)):
                v = lowpass_filtered_list[local_maxima[i] + pixels, iline]
                max_list.append(v)
            max_v = max(max_list)
            local_maxima = np.where(lowpass_filtered_list[:, iline] == max_v)[0][0]
            print("local maximum position:", local_maxima)
          
        elif len(local_maxima) == 1:
            local_maxima = local_maxima[0] + pixels
            print("local maximum position:", local_maxima)
          
        else:
            local_maxima = None # no local maxima detected
            print("local maximum position:", local_maxima)
        y.append(local_maxima)

    distance_center = np.arange(-distance_from_center, distance_from_center + 0.1, pixel_size)
    distance_list = []
  
    for i in range(len(y)):
      
        if y[i] == None:
            continue
          
        distance = distance_center[y[i]]
        distance_list.append(distance)

    # flip the location for the radial function
    radius = np.arange(0, distance_from_center + 0.1, pixel_size)
    flipped_position_list = []
  
    for j in range(len(y)):
      
        if y[j] == None:
            continue
          
        if y[j] < nrows//2:
            flip = (nrows//2) - y[j]
            distance_radius = radius[flip]
            flipped_position_list.append(distance_radius)
          
        else:
            distance_radius = radius[y[j] - nrows//2]
            flipped_position_list.append(distance_radius)

    return y, distance_list, flipped_position_list, kymo

trajectory_list = []
distance_from_center_list = []
radius_list = []

# tracking particle on kymograph
traj, dist, rad, kymo_image = track_cp_kymo(inputdir, data_name, pixel_size, top_pixels, bottom_pixels, border, distance_from_center, cutoff_length)

trajectory_list.append(traj)
distance_from_center_list.append(dist)
radius_list.append(rad)

# save the kymograph image with the trajectory
plt.plot(traj, color='k', linewidth=0.8, alpha=0.8)
plt.imshow(kymo_image, cmap='jet') # vmin=-18, vmax=5
plt.tick_params(left=False, right=False, labelleft=False, labelbottom=False, bottom=False)
plt.axis('off')
plt.savefig(inputdir + "/" + "trajectory_overlaid_kymo.png", dpi=350)

flatten_trajectory_list = [x for sublist in trajectory_list for x in sublist if x is not None]
flatten_distance_from_center_list = [x for sublist in distance_from_center_list for x in sublist]
flatten_radius_list = [x for sublist in radius_list for x in sublist]

# save the trajectory in a csv file (pixel positions, distance from center in nm, and radius from center in nm)
df_full = pd.DataFrame({"trajectory_position_in_pixel": flatten_trajectory_list, "distance_from_center_in_nm": flatten_distance_from_center_list, "radius_from_center_in_nm": flatten_radius_list})
df_full.to_csv(inputdir + "/" + "trajectory.csv", index=False)
