import math
from typing import List
from nbt import nbt
import io
import zlib
import numpy as np


class Section:
    def __init__(self, nbt: nbt.TAG_Compound):
        self.nbt = nbt
        self.palette = list(nbt["block_states"]["palette"])
        if len(self.palette) == 1:
            return
        self.data = list(nbt["block_states"]["data"])
        self.indexLength = max(math.ceil(math.log2(len(self.palette))), 4)
        self.indiciesPerLong = 64 // self.indexLength
        self.y = int(nbt["Y"].value)

    def getBlockAt(self, x: int, y: int, z: int) -> str:
        if len(self.palette) == 1:
            return self.palette[0]["Name"]
        y = y - self.y * 16
        if self.data == []:
            return self.palette[0]
        pos = y * 256 + z * 16 + x
        indexOfLong = pos // self.indiciesPerLong
        remainder = pos % self.indiciesPerLong
        paletteIndex = (self.data[indexOfLong] >> (remainder * self.indexLength)) & (
            2**self.indexLength - 1
        )
        return self.palette[paletteIndex]["Name"]


class Chunk:
    def __init__(self, nbt: nbt.TAG_Compound):
        self.nbt = nbt
        self.heightMap = np.zeros((16, 16), dtype=int)
        self.sections: List[Section] = []
        self.offset = -nbt["sections"][0]["Y"].value

    def readHeightMap(self):
        heightMaps = self.nbt["Heightmaps"]["WORLD_SURFACE"]
        self.heightMap = np.zeros((16, 16), dtype=int)
        currentX = 0
        currentZ = 0
        for h in heightMaps:
            for i in range(7):
                if currentX > 15:
                    currentX = 0
                    currentZ += 1
                if currentZ > 15:
                    break
                self.heightMap[currentX][currentZ] = ((h >> 9 * i) & 0x1FF) - 65
                currentX += 1

    def processChunk(self):
        minY = math.floor(self.heightMap.min() / 16) + self.offset
        maxY = math.floor(self.heightMap.max() / 16) + self.offset
        self.lowestSection = minY
        # we can add some pruning here to remove sections that are not needed
        sectionsToProcess = list(self.nbt["sections"])[minY : maxY + 1]
        for section in sectionsToProcess:
            self.sections.append(Section(section))

    def getTopBlockAt(self, x, z) -> str:
        y = self.heightMap[x][z]
        sectionY = y // 16
        section: Section = self.sections[sectionY - self.lowestSection + self.offset]
        return section.getBlockAt(x, y, z)


class Region:
    def __init__(self, filename, x, z):
        self.x = x
        self.z = z
        self.file = open(
            filename,
            "rb",
        )

    def __destroy__(self):
        self.file.close()

    # Reads the first and second table of the region file
    # and creates the firstTabeList
    def readTables(self):
        self.firstTable = self.file.read(4096)
        self.secondTable = self.file.read(4096)

        firstTableList = []
        for i in range(0, 4096, 4):
            offset = (
                (self.firstTable[i] << 16)
                | (self.firstTable[i + 1] << 8)
                | self.firstTable[i + 2]
            )
            size = self.firstTable[i + 3] * 4096
            firstTableList.append([offset * 4096, size])

        self.firstTableList = firstTableList

    def readChunk(self, x, z) -> Chunk:
        locationEntry = (x % 32) + ((z % 32) * 32)
        offset, size = self.firstTableList[locationEntry]
        if size == 0 and offset == 0:
            raise Exception("Chunk not generated")
        self.file.seek(offset)
        chunkData = self.file.read(size)
        decompressedData = zlib.decompress(chunkData[5:])
        nbtFile = nbt.NBTFile(buffer=io.BytesIO(decompressedData))
        if str(nbtFile["Status"]) != "minecraft:full":
            raise Exception("Chunk not fully generated")
        return Chunk(nbtFile)
