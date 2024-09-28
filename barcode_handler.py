from pyzbar.pyzbar import decode
from PIL import Image
import io


class BarcodeHandler:
    """
    Class to handle barcode extraction from images.
    """

    def extract_barcode(self, image_bytes) -> str or None:
        """
        Extracts the barcode from the given image bytes.
        """
        image = Image.open(io.BytesIO(image_bytes))
        barcodes = decode(image)
        if barcodes:
            return barcodes[0].data.decode('utf-8')
        return None
