"""
text_extraction/ocr.py

Copyright (C) 2024 Austin Berrio

A command-line OCR tool that performs various image processing operations and extracts text from images.

Image Processing Module:
- This module provides the `ImageProcessor` class for performing various image processing tasks.
- The class includes methods for loading an image, performing operations such as grayscale conversion, scaling, rotation, contrast enhancement, burning, and text extraction.
- It utilizes the OpenCV library for image processing operations and the pytesseract library for text extraction.

Classes:
- ImageProcessor: A class for image processing tasks.

Usage:
    from pygptprompt.processor.image import ImageProcessor

    # Create an instance of ImageProcessor
    processor = ImageProcessor("path/to/image.jpg")

    # Perform image processing tasks
    processor.grayscale_image()
    processor.scale_image(0.5)
    processor.rotate_image(45)
    processor.contrast_image()
    processor.burn_image(alpha=1.5, beta=-30)
    processor.preprocess_image()
    extracted_text = processor.extract_text_from_image()

For more information about OpenCV:
    https://docs.opencv.org/4.x/
For more information about image thresholding:
    https://docs.opencv.org/4.x/d7/d4d/tutorial_py_thresholding.html
For more information about image erosion and dilation:
    https://docs.opencv.org/3.4/db/df6/tutorial_erosion_dilatation.html
"""

import argparse

import cv2
import numpy as np
import pytesseract


class ImageProcessor:
    def __init__(self, file_path: str) -> None:
        """
        Initialize an ImageProcessor object.

        Parameters:
        - file_path: The path to the image file.

        This method loads the image file specified by `file_path` and creates two copies
        of it: `self.image` and `self.base_image`.
        """
        self.image: np.ndarray = np.ndarray((0, 0))
        self.base_image: np.ndarray = np.ndarray((0, 0))
        self.load_image(file_path)

    def load_image(self, file_path: str) -> None:
        """
        Load an image from a file.

        Parameters:
        - file_path: The path to the image file.

        This method uses OpenCV's `imread` function to read the image file from `file_path`.
        It creates a copy of the image and assigns it to `self.image` and `self.base_image`.
        """
        self.image = cv2.imread(file_path)
        self.base_image = self.image.copy()

    def grayscale_image(self) -> None:
        """
        Convert the image to grayscale.

        This method applies the BGR to grayscale conversion using OpenCV's `cvtColor`
        function and updates `self.image` with the grayscale version.
        """
        self.image = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)

    def scale_image(self, n: float) -> None:
        """
        Scale the image by a factor.

        Parameters:
        - n: The scaling factor.

        This method resizes the image dimensions proportionally based on the given scaling
        factor `n` using OpenCV's `resize` function with the interpolation method set to
        `cv2.INTER_AREA`. It updates `self.image` with the scaled version.
        """
        height, width = self.image.shape[:2]
        self.image = cv2.resize(
            self.image,
            (int(width * n), int(height * n)),
            interpolation=cv2.INTER_AREA,
        )

    def rotate_image(self, angle: float) -> None:
        """
        Rotate the image.

        Parameters:
        - angle: The rotation angle in degrees.

        This method rotates the image by the specified angle around its center using
        OpenCV's `getRotationMatrix2D` and `warpAffine` functions. It updates `self.image`
        with the rotated version.
        """
        height, width = self.image.shape[:2]
        image_center = (width / 2, height / 2)
        rotation_matrix = cv2.getRotationMatrix2D(image_center, angle, 1)
        self.image = cv2.warpAffine(self.image, rotation_matrix, (width, height))

    def contrast_image(self) -> None:
        """
        Enhance the image contrast.

        This method improves the contrast of the image by applying histogram equalization
        using OpenCV's `equalizeHist` function. It updates `self.image` with the enhanced
        version.
        """
        self.image = cv2.equalizeHist(self.image)

    def burn_image(self, alpha: float = 1.0, beta: int = -50) -> None:
        """
        Burn an image by adjusting brightness and contrast.

        Parameters:
        - alpha: The contrast control (1.0-3.0).
        - beta: The brightness control (-50 to 50).

        This method adjusts the brightness and contrast of the image using OpenCV's
        `convertScaleAbs` function with the specified alpha and beta values. It updates
        `self.image` with the modified version.
        """
        self.image = cv2.convertScaleAbs(self.image, alpha=alpha, beta=beta)

    def preprocess_image(self) -> None:
        """
        Preprocess the image for text extraction.

        This method applies adaptive thresholding, dilation, and erosion operations to the
        image using OpenCV's `adaptiveThreshold`, `dilate`, and `erode` functions. It
        updates `self.image` with the preprocessed version.
        """
        binary = cv2.adaptiveThreshold(
            self.image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        kernel = np.ones((1, 1), np.uint8)
        dilated = cv2.dilate(binary, kernel, iterations=1)
        self.image = cv2.erode(dilated, kernel, iterations=1)

    def extract_text_from_image_contours(self) -> str:
        """
        Find contours in the image and extract text from regions.

        Returns:
        - extracted_text: The extracted text from the image.

        This method uses OpenCV's `findContours` function to detect contours in the image.
        The contours are sorted based on their y-coordinate, and text is extracted from
        each contour region using pytesseract's `image_to_string` function. The extracted
        text is returned as a single string.
        """
        try:
            contours, _ = cv2.findContours(
                self.image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
        except cv2.error as e:
            print(e)
            print(
                "The image format is unsupported.",
                "Try converting the image to grayscale first with -g.",
            )
            exit(1)

        contours = sorted(contours, key=lambda x: cv2.boundingRect(x)[1])
        extracted_text = ""
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            roi = self.base_image[y : y + h, x : x + w]
            extracted_text += pytesseract.image_to_string(roi)
        return extracted_text

    def extract_text_from_image(self) -> str:
        """
        Extract text from the current image.

        Returns:
        - extracted_text: The extracted text from the image.

        This method uses pytesseract's `image_to_string` function to extract text from the
        current image and returns it as a string.
        """
        extracted_text = pytesseract.image_to_string(self.image)
        return extracted_text


def get_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Perform image processing operations and extract text from images."
    )
    parser.add_argument(
        "-i",
        "--image_path",
        required=True,
        type=str,
        help="The file path to the input image.",
    )
    parser.add_argument(
        "-o",
        "--text_path",
        type=str,
        default="",
        help="The file path to save the extracted text. Default is an empty string (print to console).",
    )
    parser.add_argument(
        "-r",
        "--rotate",
        type=int,
        default=0,
        help="Rotate the image by the specified angle in degrees. Default is 0.",
    )
    parser.add_argument(
        "-s",
        "--scale",
        type=int,
        default=0,
        help="Scale the image by the specified factor. Default is 0.",
    )
    parser.add_argument(
        "-g",
        "--grayscale",
        action="store_true",
        help="Convert the image to grayscale.",
    )
    parser.add_argument(
        "-a",
        "--contrast",
        action="store_true",
        help="Enhance the image contrast.",
    )
    parser.add_argument(
        "-b",
        "--burn",
        action="store_true",
        help="Burn the image by adjusting brightness and contrast.",
    )
    parser.add_argument(
        "-p",
        "--preprocess",
        action="store_true",
        help="Preprocess the image for text extraction using adaptive thresholding and erosion-dilation.",
    )
    parser.add_argument(
        "-u",
        "--contours",
        action="store_true",
        help="Extract text from image using contours and bounding rectangular areas.",
    )
    return parser.parse_args()


def main(args: argparse.Namespace):
    """
    Perform image processing operations and extract text from images.
    """
    processor = ImageProcessor(args.image_path)

    if args.rotate:
        processor.rotate_image(args.rotate)

    if args.scale:
        processor.scale_image(args.scale)

    if args.grayscale:
        processor.grayscale_image()

    if args.contrast:
        processor.contrast_image()

    if args.burn:
        processor.burn_image()

    if args.preprocess:
        processor.preprocess_image()

    if args.contours:
        text = processor.extract_text_from_image_contours()
    else:
        text = processor.extract_text_from_image()

    if args.text_path:
        with open(args.text_path, "w") as plaintext:
            plaintext.writelines(text.splitlines())
    else:
        print(text)


if __name__ == "__main__":
    args = get_arguments()
    main(args)
