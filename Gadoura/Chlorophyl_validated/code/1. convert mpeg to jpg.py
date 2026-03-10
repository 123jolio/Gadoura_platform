import cv2
import os

def mpeg_to_jpgs(video_path, output_folder='jpgs', seconds_per_frame=1):
    """
    Extracts frames from a video file and saves them as JPG images.
    """
    # Create the output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"✅ Created output folder: {output_folder}")

    # Open the video file
    video_capture = cv2.VideoCapture(video_path)
    if not video_capture.isOpened():
        print(f"❌ Error: Could not open video file at {video_path}")
        return

    # Get the frames per second (fps) of the video
    fps = video_capture.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        print("⚠️ Warning: Could not determine video FPS. Assuming 30.")
        fps = 30 # Default to 30 if FPS is not available

    # Calculate the interval in terms of frame numbers
    frame_interval = int(fps * seconds_per_frame)
    
    print(f"ℹ️ Video Info: FPS is {fps:.2f}. Saving one frame every {frame_interval} frames (approx. {seconds_per_frame} second(s)).")

    frame_count = 0
    saved_frame_count = 0
    
    while True:
        # Read the next frame from the video
        success, frame = video_capture.read()

        # If there are no more frames, break the loop
        if not success:
            break

        # Check if the current frame is at the desired interval
        if frame_count % frame_interval == 0:
            # Construct the output filename
            output_file_path = os.path.join(output_folder, f"frame_{saved_frame_count:06d}.jpg")
            
            # Save the frame as a JPG image
            cv2.imwrite(output_file_path, frame)
            saved_frame_count += 1
        
        frame_count += 1
    
    # Release the video capture object
    video_capture.release()
    print(f"\n✅ Processing complete. Extracted {saved_frame_count} frames into the '{output_folder}' folder.")


if __name__ == '__main__':
    # --- Configuration ---
    # Set the time interval (in seconds) for saving frames.
    # 1 = save one frame every second. To save ALL frames, use a very small number like 0.01
    interval = 1 

    current_dir = os.getcwd()
    
    # Define common video file extensions
    video_extensions = ['.mpeg', '.mpg', '.mp4', '.avi', '.mov']

    # Find the first video file in the current directory
    video_file_found = None
    for f in os.listdir(current_dir):
        if f.lower().endswith(tuple(video_extensions)):
            video_file_found = f
            break
            
    if video_file_found:
        video_path = os.path.join(current_dir, video_file_found)
        print(f"▶️ Found video file to convert: {video_path}")
        mpeg_to_jpgs(video_path, seconds_per_frame=interval)
    else:
        print(f"❌ No video file ({', '.join(video_extensions)}) found in the current directory.")