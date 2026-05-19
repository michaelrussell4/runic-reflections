
import os

def concatenate_markdown_files(input_dir, output_file):
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for root, _, files in os.walk(input_dir):
            for file in files:
                if file.endswith('.md') and file != '_template.md':
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r', encoding='utf-8') as infile:
                        outfile.write(f"\n# {file.replace('.md', '')}\n\n")
                        outfile.write(infile.read())
                        outfile.write("\n---\n\n")

if __name__ == "__main__":
    input_directory = "content/poetry"
    output_filename = "all_poetry.md"
    concatenate_markdown_files(input_directory, output_filename)
    print(f"All markdown files from {input_directory} concatenated into {output_filename}")
