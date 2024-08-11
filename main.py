import numpy as np
from PIL import Image
import reader as r
import os
from sys import argv
import multiprocessing as mp

OUTPUT_FOLDER = "./world_map"
regionsFilePath = ""


def parseColor(color: str) -> list:
    color = color.strip()
    color = color[1:-1]
    channels = color.split(",")
    red = int(channels[0].strip())
    green = int(channels[1].strip())
    blue = int(channels[2].strip())
    return [red, green, blue]


def loadColorsHash(filename: str) -> dict:
    file = open(filename, "r")
    lines = file.read().splitlines()

    colorsh = {}

    for i in range(0, len(lines), 2):
        colorsh[lines[i].strip()] = parseColor(lines[i + 1])
    return colorsh


def processRegion(x, z, regionsFilePath):
    colorsHash = loadColorsHash("colors.txt")
    matrix = np.zeros((32 * 16, 32 * 16, 3), dtype=np.uint8)
    filename = f"{regionsFilePath}/r.{x}.{z}.mca"
    region = r.Region(filename, x, z)
    region.readTables()
    for chunkx in range(32):
        for chunkz in range(32):
            try:
                chunk = region.readChunk(chunkx, chunkz)
            except:  # noqa: E722
                continue
            chunk.readHeightMap()
            chunk.processChunk()
            for blockx in range(16):
                for blockz in range(16):
                    block = str(chunk.getTopBlockAt(blockx, blockz))
                    id = block[10:]
                    color = colorsHash.get(id)
                    if color is None:
                        continue
                    matrix[chunkz * 16 + blockz][chunkx * 16 + blockx] = color

    img = Image.fromarray(matrix, "RGB")
    img.save(f"./{OUTPUT_FOLDER}/region.{x}.{z}.png")


def getAllRegions(regionsFilePath):
    return list(filter(lambda x: x.endswith(".mca"), os.listdir(regionsFilePath)))


def stichImages(images: list):
    print("Stiching images")
    xs = []
    zs = []
    for image in images:
        x, z = image.split(".")[1:-1]
        x = int(x)
        z = int(z)
        xs.append(x)
        zs.append(z)
    minX = min(xs)
    maxX = max(xs)
    minZ = min(zs)
    maxZ = max(zs)
    width = (maxX - minX + 1) * 512
    height = (maxZ - minZ + 1) * 512
    im = Image.new("RGB", (width, height))
    for image in images:
        x, z = image.split(".")[1:-1]
        x = int(x)
        z = int(z)
        img = Image.open(f"./{OUTPUT_FOLDER}/" + image)

        im.paste(img, ((x - minX) * 512, (z - minZ) * 512))
    im.save(f"./{OUTPUT_FOLDER}/world.png")
    print("Done stiching images")


def main():
    regions = getAllRegions(regionsFilePath)
    regionOuts = []
    for region in regions:
        x, z = region.split(".")[1:-1]
        print(f"Starting region {x} {z}")
        processRegion(int(x), int(z), regionsFilePath)
        regionOuts.append(f"region.{x}.{z}.png")
        print("Done region")
    stichImages(regionOuts)


def processRegionMultithreaded(region):
    x, z = region.split(".")[1:-1]
    print(f"Starting region {x} {z}")
    processRegion(int(x), int(z), regionsFilePath)
    print("Done region")
    return f"region.{x}.{z}.png"


def mainMultithreaded():
    regions = getAllRegions(regionsFilePath)

    pool = mp.Pool()
    pool = mp.Pool(processes=mp.cpu_count())
    regionOuts = pool.map(processRegionMultithreaded, regions)

    stichImages(regionOuts)


if __name__ == "__main__":
    regionsFilePath = argv[1] if len(argv) > 1 else ""
    if regionsFilePath == "":
        print("ERROR: Please provide a path to the regions folder")
        exit(1)

    mode = argv[2] if len(argv) > 2 else "single"

    if not os.path.exists(OUTPUT_FOLDER):
        os.mkdir(OUTPUT_FOLDER)

    if mode == "multi":
        print("Starting multithreaded")
        mainMultithreaded()
    else:
        print("Starting singlethreaded")
        main()
