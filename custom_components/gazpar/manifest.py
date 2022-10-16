import json
import os


# --------------------------------------------------------------------------------------------
class Manifest:

    # ---------------------------------
    @staticmethod
    def version():

        manifestFilePath = f"{os.path.dirname(__file__)}/manifest.json"

        with open(manifestFilePath) as jsonFile:
            manifest = json.load(jsonFile)

        return manifest["version"]
