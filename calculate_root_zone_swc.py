import rasterio
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt

def read_swc_raster(file_path):
    """Read SWC raster file and return the data as a 2D array"""
    with rasterio.open(file_path) as src:
        data = src.read(1)  # Read first band
        no_data = src.nodata
        # Mask no-data values but keep 2D structure and convert units
        data = np.where(data == no_data, np.nan, data / 1000.0)  # Convert to m³/m³
        # Convert to float64 to handle NaN values better
        data = data.astype(np.float64)
    return data

def calculate_root_zone_swc(swc_values, dates, T=10):
    """
    Calculate root zone soil water content using exponential filter
    Args:
        swc_values: List of 2D arrays containing surface SWC values
        dates: List of corresponding dates
        T: Time constant in days (default 10 days for ~1m root zone)
    Returns:
        2D array of root zone SWC values
    """
    if len(swc_values) == 0:
        return None
        
    # Get the shape from the first valid array
    shape = swc_values[0].shape
    print(f"Data shape: {shape}")
    
    # Initialize with first valid observation
    root_zone_swc = np.copy(swc_values[0])
    gain = np.ones(shape)
    reference_date = dates[0]
    
    print(f"Initial SWC range: {np.nanmin(root_zone_swc):.4f} to {np.nanmax(root_zone_swc):.4f}")
    
    # Apply recursive filter
    for i in range(1, len(dates)):
        # Calculate time difference in days
        delta_days = (dates[i] - reference_date).total_seconds() / (24 * 3600)
        
        # Update gain (handle NaN values)
        # gain = np.where(
        #     ~np.isnan(swc_values[i]),
        #     gain / (gain + np.exp(-delta_days / T)),
        #     gain
        # )
        gain = np.where(
            (~np.isnan(swc_values[i])) & (swc_values[i] != 0),  # Excluye NaN y ceros
            gain / (gain + np.exp(-delta_days / T)),
            gain
)

        # Update root zone SWC (handle NaN values)
        diff = swc_values[i] - root_zone_swc
        update = gain * diff
        root_zone_swc = np.where(
            ~np.isnan(update),
            root_zone_swc + update,
            root_zone_swc
        )
        
        # Print progress
        if i % 10 == 0:
            print(f"Processed {i}/{len(dates)} dates")
            print(f"Current SWC range: {np.nanmin(root_zone_swc):.4f} to {np.nanmax(root_zone_swc):.4f}")
        
        # Update reference date
        reference_date = dates[i]
    
    return root_zone_swc

def main():
    # Get all raster files
    raster_folder = "H:/Sensors/reproyectado"
    raster_files = sorted([f for f in Path(raster_folder).glob("*.tif") 
                          if not f.stem.endswith('-qf')])
    
    if not raster_files:
        print("No raster files found")
        return
        
    print(f"Found {len(raster_files)} raster files")
    
    # Load all data
    swc_data = []
    dates = []
    
    for file_path in raster_files:
        try:
            # Extract date from filename
            filename = file_path.stem
            date_str = filename.split('_')[0]
            date = datetime.strptime(date_str, '%Y%m%d')
            
            # Read raster data
            data = read_swc_raster(file_path)
            
            # Basic validation
            if np.all(np.isnan(data)):
                print(f"Skipping {file_path.name} - All values are NaN")
                continue
                
            valid_range = (0, 1)  # SWC should be between 0 and 1
            if np.nanmin(data) < valid_range[0] or np.nanmax(data) > valid_range[1]:
                print(f"Warning: {file_path.name} has values outside expected range {valid_range}")
            
            swc_data.append(data)
            dates.append(date)
            print(f"Successfully loaded {file_path.name} - Valid range: {np.nanmin(data):.4f} to {np.nanmax(data):.4f}")
            
        except Exception as e:
            print(f"Error processing {file_path.name}: {str(e)}")
            continue
    
    if not swc_data:
        print("No valid data loaded")
        return
        
    # Create output directory for root zone SWC files
    output_dir = Path("H:/Sensors/root_zone")
    output_dir.mkdir(exist_ok=True)
    
    # Save root zone SWC for each date
    root_zone_swc_data = []
    print("\nCalculating and saving root zone SWC for each date...")
    
    # Copy metadata from first file
    with rasterio.open(raster_files[0]) as src:
        profile = src.profile.copy()
        profile.update(dtype='float32')
    
    for i, date in enumerate(dates):
        # Calculate root zone SWC up to this date
        current_root_zone_swc = calculate_root_zone_swc(swc_data[:i+1], dates[:i+1])
        
        if current_root_zone_swc is not None:
            # Save statistics for plotting
            root_zone_swc_data.append({
                'date': date,
                'mean_root_zone_swc': np.nanmean(current_root_zone_swc),
                'median_root_zone_swc': np.nanmedian(current_root_zone_swc),
                'std_root_zone_swc': np.nanstd(current_root_zone_swc),
                'min_root_zone_swc': np.nanmin(current_root_zone_swc),
                'max_root_zone_swc': np.nanmax(current_root_zone_swc)
            })
            
            # Save raster file
            output_file = output_dir / f"root_zone_SWC-{date.strftime('%Y%m%d')}_cws.tiff"
            with rasterio.open(output_file, 'w', **profile) as dst:
                dst.write(current_root_zone_swc.astype('float32'), 1)
            
            if (i + 1) % 10 == 0:
                print(f"Processed {i + 1}/{len(dates)} dates")
    
    # Convert statistics to DataFrame
    stats_df = pd.DataFrame(root_zone_swc_data)
    stats_df.set_index('date', inplace=True)
    
    # Save statistics to CSV
    stats_df.to_csv('root_zone_swc_statistics.csv')
    print("\nSaved statistics to root_zone_swc_statistics.csv")
    
    # Create time series visualization
    plt.figure(figsize=(12, 6))
    
    # Plot mean and range
    plt.fill_between(stats_df.index, 
                     stats_df['mean_root_zone_swc'] - stats_df['std_root_zone_swc'],
                     stats_df['mean_root_zone_swc'] + stats_df['std_root_zone_swc'],
                     alpha=0.3, label='±1 std dev')
    
    plt.plot(stats_df.index, stats_df['mean_root_zone_swc'], 
             label='Mean Root Zone SWC', linewidth=2)
    plt.plot(stats_df.index, stats_df['median_root_zone_swc'], 
             label='Median Root Zone SWC', linewidth=2, linestyle='--')
    
    plt.xlabel('Date')
    plt.ylabel('Root Zone SWC (m³/m³)')
    plt.title('Root Zone Soil Water Content Over Time')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig('root_zone_swc_timeseries.png', dpi=300, bbox_inches='tight')
    print("Saved time series plot to root_zone_swc_timeseries.png")
    
    # Create comparison visualization for the last date
    plt.figure(figsize=(12, 5))
    
    plt.subplot(121)
    im1 = plt.imshow(swc_data[-1], cmap='YlOrBr')
    plt.colorbar(im1, label='Surface SWC (m³/m³)')
    plt.title(f'Surface SWC\n{dates[-1].strftime("%Y-%m-%d %H:%M")}')
    
    plt.subplot(122)
    im2 = plt.imshow(current_root_zone_swc, cmap='YlOrBr')
    plt.colorbar(im2, label='Root Zone SWC (m³/m³)')
    plt.title(f'Root Zone SWC\n{dates[-1].strftime("%Y-%m-%d %H:%M")}')
    
    plt.tight_layout()
    plt.savefig('swc_comparison.png', dpi=300, bbox_inches='tight')
    print("Saved spatial comparison to swc_comparison.png")

if __name__ == "__main__":
    main() 