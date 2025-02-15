import asyncio
import json
import os


# --------------------------------------------------------------------------------------------
class Manifest:

    # ---------------------------------
    @staticmethod
    async def version():

        manifestFilePath = f"{os.path.dirname(__file__)}/manifest.json"

        loop = asyncio.get_event_loop()
        manifest = await loop.run_in_executor(None, Manifest.load_manifest, manifestFilePath)

        return manifest["version"]

    # ---------------------------------
    @staticmethod
    def load_manifest(manifestFilePath: str):
        with open(manifestFilePath, "r", encoding="utf-8") as jsonFile:
            manifest = json.load(jsonFile)
        return manifest
