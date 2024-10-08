import json
import os
import asyncio


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
    def load_manifest(manifestFilePath):
        with open(manifestFilePath) as jsonFile:
            manifest = json.load(jsonFile)
        return manifest
