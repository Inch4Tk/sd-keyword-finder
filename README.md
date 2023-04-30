# SD Keyword Finder
Commandline keyword (trigger words) finder for Stable Diffusion civitai.com Models and Loras. 

## Installation
Currently the A1111 extension https://github.com/mix1009/model-keyword is used to supply the keywords. 

Option 1:
- Install the full extension if you use A1111 anyways.

Option 2:
- There is no direct dependency to A1111 or the extension, so you can also just download the "lora-keyword.txt" and "model-keyword.txt" files from the extension's github and store them in any local folder without installing the full extension.

Then in any folder
```
git clone https://github.com/Inch4Tk/sd-keyword-finder
cd sd-keyword-finder
pip install -r requirements.txt
```

Copy and rename the "config-example.json" to "config.json". Then point the "model_keyword_path" to the folder containing "lora-keyword.txt" and "model-keyword.txt". Also point both "lora_path" and "sd_model_path" to the corresponding dir where you store Loras and SD Models.

## Usage
The keyword finder will perform a fuzzy search for your search string among all your installed models and loras. Then compares all found matches with the keyword database.
```
python kwfinder.py moxin

# Result:
# Search word: moxin, found 2 installed matches, 1 keyword matches
# 
# Found the following fuzzy matches, but no associated keywords (incomplete store or model has no kws):
# Name                            Hash
# Moxin_Shukezouma11.safetensors  8e0e71af
# 
# Found these fuzzy matches:
# Type   User  Name                            Hash      Keywords
# lora   false Moxin_10.safetensors            aea008ef  shuimobysim|wuchangshuo|bonian|zhenbanqiao|badashanren
```
We found keywords associated with the moxin lora, but have no special keywords associated with the shukezouma version, since they are missing in the db.

It can also be used to update the keyword database custom files from the commandline
```
python kwfinder.py --update Moxin_Shukezouma11.safetensors "random|keywords|inserted"

# Now the search returns:
# Search word: moxin, found 2 installed matches, 2 keyword matches
#
# Found these fuzzy matches:
# Type   User  Name                            Hash      Keywords
# lora   false Moxin_10.safetensors            aea008ef  shuimobysim|wuchangshuo|bonian|zhenbanqiao|badashanren
# lora   true  Moxin_Shukezouma11.safetensors  8e0e71af  random|keywords|inserted
```
We inserted custom (wrong) keywords for the Moxin_Shukezouma Lora.

Finally we can also delete the wrong entry again using
```
python kwfinder.py --update Moxin_Shukezouma11.safetensors ""
```
