import json
import os
import argparse
from collections import defaultdict
from fuzzysearch import find_near_matches

def model_hash(filename):
    """Hash-function from stable-diffusion-webui/modules/sd_models.py:"""
    try:
        with open(filename, "rb") as file:
            import hashlib
            m = hashlib.sha256()

            file.seek(0x100000)
            m.update(file.read(0x10000))
            return m.hexdigest()[0:8]
    except FileNotFoundError:
        return 'NOFILE'


def load_local_hash_memory():
    if os.path.isfile("local_hashmem.json"):
        with open("local_hashmem.json", "r") as f:
            return json.load(f)
    else:
        return dict()

def searchname_from_lora(lora):
    return f"lora_{lora.rsplit('.')[0]}".lower()

def searchname_from_model(model):
    return f"model_{model.rsplit('.')[0]}".lower()

def scan_and_update_hash_memory(config, hashmem: dict):
    loras = os.listdir(config["lora_path"])
    loras = [f for f in loras if os.path.isfile(os.path.join(config["lora_path"], f))]
    models = os.listdir(config["sd_model_path"])
    models = [f for f in models if os.path.isfile(os.path.join(config["sd_model_path"], f))]

    changed = False
    searched_for = set()
    for lora in loras:
        if ".txt" in lora:
            continue
        searchname = searchname_from_lora(lora)
        searched_for.add(searchname)
        if not searchname in hashmem:
            hashmem[searchname] = [model_hash(os.path.join(config["lora_path"], lora)), lora]
            changed = True

    for model in models:
        if ".txt" in model:
            continue
        searchname = searchname_from_model(model)
        searched_for.add(searchname)
        if not searchname in hashmem:
            hashmem[searchname] = [model_hash(os.path.join(config["sd_model_path"], model)), model]
            changed = True

    leftover = set(hashmem.keys()).difference(searched_for)
    for lo in leftover:
        print(lo)
        del hashmem[lo]

    if changed:
        with open("local_hashmem.json", "w") as f:
            json.dump(hashmem, f)

    return hashmem


def parse_keyword_line(line: str):
    l = line.strip()
    if l.startswith("#"):
        return None
    items = l.split(",")
    return items[0].strip(), items[1].strip(), None if len(items) < 3 else items[2].strip()


def parse_keyword_file(file):
    if not os.path.isfile(file):
        print(f"Warning: Failed to load keyword store {file}")
        return dict()

    mapping = dict()
    with open(file, "r", encoding="utf8") as f:
        for line in f:
            kwline = parse_keyword_line(line)
            if kwline is not None:
                mhash, keywords, name = kwline
                mapping[mhash] = (keywords, name)

    return mapping


def load_keyword_maps(config):
    maps = {
        "lora": parse_keyword_file(os.path.join(config["model_keyword_path"], "lora-keyword.txt")),
        "lora_u": parse_keyword_file(os.path.join(config["model_keyword_path"], "lora-keyword-user.txt")),
        "model": parse_keyword_file(os.path.join(config["model_keyword_path"], "model-keyword.txt")),
        "model_u": parse_keyword_file(os.path.join(config["model_keyword_path"], "custom-mappings.txt")),
    }
    return maps


def print_search_result_line(type, user, name, hash, keywords, name_padding):
    print(f"{type: <7}{user: <6}{name: <{name_padding}}{hash: <10}{keywords}")


def print_type_results(results, category, category_nice, name_padding, is_custom):
    if not category in results:
        return
    for (name, hash, keywords, mk_name) in results[category]:
        print_search_result_line(category_nice, "true" if is_custom else "false", name, hash, keywords, name_padding)

def search(hashmem, keywords, ss):
    # Check our hash memory with fuzzy search
    ss = ss.lower()
    found_matches = list()
    max_match_name_len = 0
    for (searchname, (hash, orig_name)) in hashmem.items():
        splitname = searchname.split("_", 1)[1]
        matches = False
        if splitname.startswith(ss): # First check if the name starts with it
            matches = True
        else:
            matches = find_near_matches(ss, splitname, max_l_dist=1)
        if matches:
            if len(orig_name) > max_match_name_len:
                max_match_name_len = len(orig_name)
            found_matches.append((hash, orig_name))

    # use the matched hashes to lookup the keywords
    results = defaultdict(list)
    matchcount = 0
    unfound_matches = list()
    for (match_hash, match_orig_name) in found_matches:
        found_any = False
        for (mapdesc, kwmap) in keywords.items():
            if match_hash in kwmap:
                results[mapdesc].append((match_orig_name, match_hash, *kwmap[match_hash]))
                matchcount += 1
                found_any = True
        if not found_any:
            unfound_matches.append((match_hash, match_orig_name))

    # output
    padding = max_match_name_len + 2
    print(f"Search word: {ss}, found {len(found_matches)} installed matches, {matchcount} keyword matches")

    if len(unfound_matches) > 0:
        print()
        print("Found the following fuzzy matches, but no associated keywords (incomplete store or model has no kws):")
        print(f"{'Name': <{padding}}Hash")
        for (hash, name) in unfound_matches:
            print(f"{name: <{padding}}{hash}")

    if len(found_matches) > 0 and matchcount > 0:
        print()
        print("Found these fuzzy matches:")
        print(f"{'Type': <7}{'User': <6}{'Name': <{padding}}{'Hash': <10}Keywords")
    print_type_results(results, "model", "model", padding, False)
    print_type_results(results, "model_u", "model", padding, True)
    print_type_results(results, "lora", "lora", padding, False)
    print_type_results(results, "lora_u", "lora", padding, True)


def update_model(hashmem, map, model, update):
    model_hash = None
    model_name = None
    is_model = None
    model_user_map = map["model_u"]
    lora_user_map = map["lora_u"]

    # Get Hash/Name
    model_sn = searchname_from_model(model)
    if model_sn in hashmem:
        model_hash, model_name = hashmem[model_sn]
        is_model = True
    model_sn = searchname_from_lora(model)
    if model_sn in hashmem:
        if model_hash is not None:
            print(f"Warning, duplicate entries for model and lora in custom mappings {model}. Please resolve updates manually.")
            return
        model_hash, model_name = hashmem[model_sn]
        is_model = False

    if is_model is None:
        print(f"Did not find a corresponding model or lora.")


    # Handle deletion
    if not update:
        if model_hash in model_user_map:
            del model_user_map[model_hash]
        if model_hash in lora_user_map:
            del lora_user_map[model_hash]
        return

    # Handle insertion
    if is_model:
        model_user_map[model_hash] = (update, model_name)
    elif not is_model:
        lora_user_map[model_hash] = (update, model_name)


def flush_map(config, file, map):
    p = os.path.join(config["model_keyword_path"], file)
    if not os.path.isfile(p):
        print(f"Failed to find keyword store that is supposed to be updated {p}")
        return
    with open(p, "w", encoding="utf8") as f:
        for mhash, (keywords, name)in map.items():
            f.write(f"{mhash}, {keywords}")
            if name is not None:
                f.write(f", {name}")
            f.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog="kwfinder.py",
                    description="Find stable diffusion keywords from your installed models and loras, utilizing data from https://github.com/mix1009/model-keyword. Requires the extension to be installed locally.")
    parser.add_argument("search_string", type=str, help="Fuzzy-Search using the Lora/Model filename")
    # parser.add_argument("-i", "--inverse", action="store_true", help="Fuzzy-Search Models and Lora's associated with a keyword.")
    parser.add_argument("--update", type=str, help="Update a custom mapping for a Model or Lora. Needs complete name with fileending. Search string is then written into the custom mapping. Use | to separate keywords. Wrap in '' when using |. Use empty '' to delete an entry.")
    args = parser.parse_args()

    config = None
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except:
        print("Failed to load config.json, make sure you copied the example and fixed the paths to your local system setup.")

    hashmem = load_local_hash_memory()
    hashmem = scan_and_update_hash_memory(config, hashmem)
    keywords = load_keyword_maps(config)

    if args.update:
        update_model(hashmem, keywords, args.update, args.search_string)
        flush_map(config, "custom-mappings.txt", keywords["model_u"])
        flush_map(config, "lora-keyword-user.txt", keywords["lora_u"])
    else:
        search(hashmem, keywords, args.search_string)

