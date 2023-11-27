import os

def create_files(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

    for letter in range(ord('c'), ord('z')+1):
        filename = os.path.join(directory, f"{chr(letter)}.txt")
        with open(filename, 'w') as file:
            pass

# Usage example
directory_path = '/Users/so/Documents/projects/asl-detection/files'
create_files(directory_path)
