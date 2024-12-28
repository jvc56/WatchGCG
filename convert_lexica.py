import argparse

# Function to process the text file
def convert_file(input_file, output_file):
    with open(input_file, "r") as infile, open(output_file, "w") as outfile:
        for line in infile:
            # Strip the line of leading/trailing whitespace
            line = line.strip()
            
            # Split by the tab character
            if "\t" in line:
                word, definition = line.split("\t", 1)
                # Format and write the output
                outfile.write(f"{word},'{definition}'\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert a tab-separated file to a comma-separated format with quoted definitions.")
    parser.add_argument("input_file", help="Path to the input file")
    parser.add_argument("output_file", help="Path to the output file")

    args = parser.parse_args()

    convert_file(args.input_file, args.output_file)

    print(f"Conversion complete. Output written to {args.output_file}.")
