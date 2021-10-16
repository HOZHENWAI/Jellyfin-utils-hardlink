import os
import argparse
import logging
import traceback
from typing import Union, List, Optional

from tqdm import tqdm
from pathlib import Path

# Log settings
logger = logging.getLogger(__name__)
streamHandler = logging.StreamHandler()
logger.setLevel(logging.INFO)
logger.addHandler(streamHandler)

class Extensions:
    """
    Class to store the extensions
    """
    mkv = ".mkv"
    avi = ".avi"
    mp4 = ".mp4"

    jpeg = ".jpeg"
    jpg = ".jpg"
    img = ".img"
    bmp = ".bmp"

    Videos = [mkv,avi, mp4]
    Pictures = [jpeg, jpg, img, bmp]

class NameMethod:
    """
    Class to store the naming resolver method
    """
    tree = "tree"
    root = "root"
    collection = "collection"


def link_folder(source:Path, destination:Path, extensions:Optional[List]=None)->None:
    """

    """
    for f in os.scandir(source):
        if not f.is_dir():
            if extensions is None:
                try:
                    os.link(src=f,dst= destination.joinpath(f.name))
                except FileExistsError:
                    pass
            elif Path(f).suffix in extensions:
                try:
                    os.link(src=f,dst= destination.joinpath(f.name))
                except FileExistsError:
                    pass

def link_subfolders(source:Path, destination:Path, extensions:Optional[List]=None)->None:
    """

    """
    link_folder(source=source, destination=destination, extensions=extensions)
    for f in os.scandir(source):
        if f.is_dir():
            resolved_destination= name_resolve(Path(f),source,destination, method=NameMethod.tree)
            try:
                os.mkdir(resolved_destination)
            except FileExistsError:
                pass
            link_subfolders(source=Path(f),destination=resolved_destination, extensions=extensions)

def link_subfolders_alternative(source:Path, destination:Path, extensions:Union[None, List]=None)->None:
    """
    Link all subfolders without recursion, ignore extensions
    """

    if not os.path.isdir(source):
        source = source.parent

    source_path_parts_l = len(source.parts)-1
    try:
        os.mkdir(destination.joinpath(source.name))
    except FileExistsError:
        pass

    for root, dirs, files in os.walk(source, topdown=True):
        for name in dirs:
            try:
                os.mkdir(Path(destination, *Path(os.path.join(root, name)).parts[source_path_parts_l:]))
            except FileExistsError:
                pass
        for name in files:
            src_path = Path(root, name)
            if extensions is None:
                try:
                    os.link(src=src_path,
                            dst=Path(destination, *Path(os.path.join(root, name)).parts[source_path_parts_l:]))
                except FileExistsError:
                    pass
            elif src_path.suffix in extensions:
                try:
                    os.link(src=src_path,
                            dst=Path(destination, *Path(os.path.join(root, name)).parts[source_path_parts_l:]))
                except FileExistsError:
                    pass

def link_collection_folders(source:Path, destination:Path, extensions:Optional[List]=None)->None:
    for obj in os.scandir(source):
        if not os.path.isdir(obj):
            prefix = " ".join(source.parts[-1].split()[:2])  # keep a prefix for the origin folder
            new_link = name_resolve(f=Path(obj), source=source, destination=destination, prefix=prefix)
            if extensions is None:
                if not os.path.exists(new_link.parent):
                    try:
                        os.mkdir(new_link.parent)
                    except FileExistsError:
                        pass

                try:
                    os.link(src=Path(obj), dst = new_link)
                except FileExistsError:
                    pass

            elif new_link.suffix in extensions:
                if not os.path.exists(new_link.parent):
                    try:
                        os.mkdir(new_link.parent)
                    except FileExistsError:
                        pass

                try:
                    os.link(src=Path(obj), dst=new_link)
                except FileExistsError:
                    pass
        else:
            link_collection_folders(Path(obj), destination, extensions)

def name_resolve(f:Path,source:Path, destination:Path, method=NameMethod.tree, prefix:Optional[str]=None)->Path:
    """
    Compute the correct name for hardlinking given an original source and destination path
    """
    if method == NameMethod.collection:
        assert not os.path.isdir(f)
    elif not os.path.isdir(f): # make sure we have a folder
        f = f.parent

    if method == NameMethod.tree:
        f_parts = f.parts
        source_parts = source.parts
        resolved_path = Path(destination,*f_parts[len(source_parts):])
    elif method == NameMethod.root:
        resolved_path = Path(destination, f.name)
    elif method == NameMethod.collection:
        f_parts = list(f.parts)
        source_parts = source.parts
        if prefix is not None:
            f_parts[-1] = prefix + " - " + f_parts[-1]
        resolved_path = Path(destination, *f_parts[len(source_parts):])
    else:
        raise NotImplementedError

    return resolved_path

def link_movies(source:Path, destination:Path)->None:
    """
    Hardlink single animated/movies/
    :param source: Path from which the scanner will search for the movies
    :param destination: Path where will be linked the movies
    :return:
    """
    try:
        link_folder(source=source,destination= destination, extensions=Extensions.Videos)
    except Exception as e:
        print(traceback.format_exc())
        pass



def link_series(source:Path, destination:Path, extensions:Optional[List]=None)->None:
    """
    Hardlink series from source to destination while forcing a flat structure
    :param source:
    :param destination:
    :return:
    """
    try:
        for f in tqdm(os.scandir(source)):
            if f.is_dir():
                contents = list(Path(f).glob("*"))
                episode_true = any([content.suffix in extensions for content in contents])
                if episode_true: # case 1: there is an episode in the folder, reproduce the tree and hardlink
                    if len(contents)<53:
                        link_subfolders_alternative(Path(f), destination, extensions)
                    else:
                        link_collection_folders(Path(f), destination, extensions)
                else: #case 2: there is no episode in the folder, then walk the other folder
                    logger.info(f)
                    link_series(Path(f), destination, extensions)
    except Exception as e:
        print(traceback.format_exc())
        pass

if __name__ == "__main__":
    # Parser config
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", "-s", type=str, default="Library")
    parser.add_argument("--destination", "-d", type=str, default= "Library-Jellyfin")
    parser.add_argument("--type", "-t", choices=["movies", "series", "pictures"])
    args = parser.parse_args()
    if args.type == "movies":
        link_movies(Path(args.source).resolve(), Path(args.destination).resolve())
    elif args.type == "series":
        link_series(Path(args.source).resolve(), Path(args.destination).resolve(), Extensions.Videos)
    elif args.type == "pictures":
        link_series(Path(args.source).resolve(), Path(args.destination).resolve(), Extensions.Pictures)
