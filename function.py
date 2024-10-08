# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import StreamingResponse, FileResponse
import shutil
from datetime import datetime
import io
import os
import cv2
from groundingdino.util.inference import Model
from segment_anything import sam_model_registry, SamPredictor
import torch
from PIL import Image
import numpy as np
from PIL import Image as Img
from typing import List
import warnings
import uuid
import aiohttp
from io import BytesIO
from diffusers import AutoPipelineForInpainting
from diffusers.utils import load_image
import torch
from torchvision import transforms
from PIL import Image
import cv2


warnings.filterwarnings("ignore")

current_directory = os.path.dirname(__file__)

GROUNDING_DINO_CONFIG_PATH = f"{current_directory}/groundingdino/config/GroundingDINO_SwinT_OGC.py"
GROUNDING_DINO_CHECKPOINT_PATH = f"{current_directory}/weights/groundingdino_swint_ogc.pth"
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
grounding_dino_model = None

SAM_ENCODER_VERSION = "vit_h"
SAM_CHECKPOINT_PATH = f"{current_directory}/weights/sam_vit_h_4b8939.pth"
sam = sam_model_registry[SAM_ENCODER_VERSION](checkpoint=SAM_CHECKPOINT_PATH).to(device=DEVICE)
sam_predictor = SamPredictor(sam)

pipe = AutoPipelineForInpainting.from_pretrained("diffusers/stable-diffusion-xl-1.0-inpainting-0.1", torch_dtype=torch.float16, variant="fp16").to("cuda")



def segment(sam_predictor: SamPredictor, image: np.ndarray, xyxy: np.ndarray) -> np.ndarray:
    sam_predictor.set_image(image)
    result_masks = []
    for box in xyxy:
        masks, scores, logits = sam_predictor.predict(
            box=box,
            multimask_output=True
        )
        index = np.argmax(scores)
        result_masks.append(masks[index])
    return np.array(result_masks)


def load_grounding_dino_model():
    global grounding_dino_model
    if grounding_dino_model is None:
        grounding_dino_model = Model(model_config_path=GROUNDING_DINO_CONFIG_PATH, model_checkpoint_path=GROUNDING_DINO_CHECKPOINT_PATH)
        print("Grounding DINO model loaded successfully")
    else:
        print("Grounding DINO model already loaded")

def enhance_class_name(class_names: List[str]) -> List[str]:
    return [f"all {class_name}s" for class_name in class_names]


def auto_crop(image_path):

    load_grounding_dino_model()

    SOURCE_IMAGE_PATH = image_path
    CLASSES = ['hair']
    BOX_TRESHOLD = 0.40
    TEXT_TRESHOLD = 0.25
    image = cv2.imread(SOURCE_IMAGE_PATH)
    # image = output_chbg_scaled

    # Detect objects and annotate the image
    detections = grounding_dino_model.predict_with_classes(
        image=image,
        classes=enhance_class_name(class_names=CLASSES),
        box_threshold=BOX_TRESHOLD,
        text_threshold=TEXT_TRESHOLD
    )

    for x1, y1, x2, y2 in detections.xyxy:
        # Extract the region of interest using bounding box coordinates
        print(y2)
        if y2 < 195:
            y2 = y2 + 50
            x1 = x1 - 20
            x2 = x2 + 20
        x1, y1, x2, y2_h = int(x1), int(y1), int(x2), int(y2)
        # cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Green rectangle
        cutout = image[y1:y2_h, x1:x2]
    
    print(f"This is the cutout {cutout}")

    output_path = f'{current_directory}/uploads/{str(uuid.uuid4())}.png'
    cv2.imwrite(output_path, cutout)
    print(f"cutout {output_path}")

    CLASSES = ['head']
    BOX_TRESHOLD = 0.42
    TEXT_TRESHOLD = 0.35

    image = cv2.imread(SOURCE_IMAGE_PATH)

    detections = grounding_dino_model.predict_with_classes(
        image=image,
        classes=enhance_class_name(class_names=CLASSES),
        box_threshold=BOX_TRESHOLD,
        text_threshold=TEXT_TRESHOLD
    )

    for box in detections.xyxy:
        x1, y1, x2, y2 = box
        print(y2)
        y2 = y2 + 10
        x1 = x1 - 20
        x2 = x2 + 20
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    
        cutout = image[y1:y2, x1:x2]

    if y2_h < y2:
        print(f"This is the cutout {cutout}")
        cv2.imwrite(output_path, cutout)
        print(f"cutout {output_path}")

    return output_path


def hair_mask(source_image_path: str) -> str:

    load_grounding_dino_model()

    CLASSES = ['hair']
    BOX_THRESHOLD = 0.40
    TEXT_THRESHOLD = 0.25

    image = cv2.imread(source_image_path)
    # Detect objects and annotate the image
    detections = grounding_dino_model.predict_with_classes(
        image=image,
        classes=enhance_class_name(class_names=CLASSES),
        box_threshold=BOX_THRESHOLD,
        text_threshold=TEXT_THRESHOLD
    )

    detections.mask = segment(
        sam_predictor=sam_predictor,
        image=cv2.cvtColor(image, cv2.COLOR_BGR2RGB),
        xyxy=detections.xyxy
    )
    
    mask_pil = Image.fromarray(detections.mask[0])

    mask_path = f"{current_directory}/uploads/{str(uuid.uuid4())}.jpg"
    mask_pil.save(mask_path)
    
    return mask_path

def head_mask(source_image_path: str) -> str:

    load_grounding_dino_model()

    CLASSES = ['head']
    BOX_TRESHOLD = 0.42
    TEXT_TRESHOLD = 0.35

    image = cv2.imread(source_image_path)

    # Detect objects and annotate the image
    detections = grounding_dino_model.predict_with_classes(
        image=image,
        classes=enhance_class_name(class_names=CLASSES),
        box_threshold=BOX_TRESHOLD,
        text_threshold=TEXT_TRESHOLD
    )

    for box in detections.xyxy:
        x1, y1, x2, y2 = box
        # Extract the region of interest using bounding box coordinates
        print(y2)
        y2 = y2 + 10
        x1 = x1 - 20
        x2 = x2 + 20
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        mask = np.zeros_like(image, dtype=np.uint8)

        # Draw a filled rectangle on the mask
        cv2.rectangle(mask, (x1, y1), (x2, y2), (255, 255, 255), thickness=cv2.FILLED)

    mask_path = f"{current_directory}/uploads/{str(uuid.uuid4())}.jpg"
    cv2.imwrite(mask_path, mask)

    return mask_path


def generate_hair_mask(source_image_path: str) -> str:

    load_grounding_dino_model()

    CLASSES = ['hair']
    BOX_THRESHOLD = 0.40
    TEXT_THRESHOLD = 0.25

    image = cv2.imread(source_image_path)
    # Detect objects and annotate the image
    detections = grounding_dino_model.predict_with_classes(
        image=image,
        classes=enhance_class_name(class_names=CLASSES),
        box_threshold=BOX_THRESHOLD,
        text_threshold=TEXT_THRESHOLD
    )

    detections.mask = segment(
        sam_predictor=sam_predictor,
        image=cv2.cvtColor(image, cv2.COLOR_BGR2RGB),
        xyxy=detections.xyxy
    )
    
    mask_pil = Image.fromarray(detections.mask[0])
    mask_path = f"{current_directory}/uploads/{str(uuid.uuid4())}.jpg"
    mask_pil.save(mask_path)

    return mask_path



def generate_preson_box_mask(source_image_path: str) -> str:

    load_grounding_dino_model()

    CLASSES = ['person']
    BOX_THRESHOLD = 0.37
    TEXT_THRESHOLD = 0.25

    image = cv2.imread(source_image_path)

    detections = grounding_dino_model.predict_with_classes(
        image=image,
        classes=enhance_class_name(class_names=CLASSES),
        box_threshold=BOX_THRESHOLD,
        text_threshold=TEXT_THRESHOLD
    )
    
    for x1, y1, x2, y2 in detections.xyxy:
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        mask = np.zeros_like(image, dtype=np.uint8)
        cv2.rectangle(mask, (x1, y1), (x2, y2), (255, 255, 255), thickness=cv2.FILLED)

        cutout = image[y1:y2, x1:x2]
        
    mask_path = f"{current_directory}/uploads/{str(uuid.uuid4())}.png"

    cv2.imwrite(mask_path,mask)

    return mask_path

def generate_inverted_mask(source_image_path: str) -> str:
    
    image = cv2.imread(source_image_path)
    inverted_image = cv2.bitwise_not(image)
    mask_path = f"{current_directory}/uploads/{str(uuid.uuid4())}.png"
    cv2.imwrite(mask_path,inverted_image)
    return mask_path


def add_padding_to_mask(mask, padding_size=5):
    # Create a kernel for dilation
    kernel = np.ones((padding_size, padding_size), np.uint8)

    # Apply dilation to the mask
    dilated_mask = cv2.dilate(mask, kernel, iterations=1)

    return dilated_mask



def generate_bob_hair(source_image_path: str) -> str:

    load_grounding_dino_model()

    CLASSES = ['hair']
    BOX_THRESHOLD = 0.60
    TEXT_THRESHOLD = 0.25

    image = cv2.imread(source_image_path)
    # Detect objects and annotate the image
    detections = grounding_dino_model.predict_with_classes(
        image=image,
        classes=enhance_class_name(class_names=CLASSES),
        box_threshold=BOX_THRESHOLD,
        text_threshold=TEXT_THRESHOLD
    )

    for x1, y1, x2, y2 in detections.xyxy:
        # Extract the region of interest using bounding box coordinates
        print(y2)
        if y2 < 195:
            y2 = y2 + 50
            x1 = x1 - 20
            x2 = x2 + 20
        x1, y1, x2, y2_h = int(x1), int(y1), int(x2), int(y2)
        mask = np.zeros_like(image, dtype=np.uint8)
        cv2.rectangle(mask, (x1, y1), (x2, y2_h), (255, 255, 255), thickness=cv2.FILLED)
    
    hair_mask_path_1 = f"{current_directory}/uploads/{str(uuid.uuid4())}.jpg"
    cv2.imwrite(hair_mask_path_1, mask)
    
    CLASSES = ['hair']
    BOX_THRESHOLD = 0.60
    TEXT_THRESHOLD = 0.25

    image = cv2.imread(source_image_path)
    # Detect objects and annotate the image
    detections = grounding_dino_model.predict_with_classes(
        image=image,
        classes=enhance_class_name(class_names=CLASSES),
        box_threshold=BOX_THRESHOLD,
        text_threshold=TEXT_THRESHOLD
    )

    detections.mask = segment(
        sam_predictor=sam_predictor,
        image=cv2.cvtColor(image, cv2.COLOR_BGR2RGB),
        xyxy=detections.xyxy
    )

    hair_mask = detections.mask[0]
    hair_mask = np.where(hair_mask, 255, 0).astype(np.uint8)
    hair_mask = add_padding_to_mask(hair_mask, padding_size=10)
    mask_pil = Image.fromarray(hair_mask)
    
    hair_mask_path_2 = f"{current_directory}/uploads/{str(uuid.uuid4())}.jpg"
    mask_pil.save(hair_mask_path_2)
    
    CLASSES = ['head']
    BOX_THRESHOLD = 0.42
    TEXT_THRESHOLD = 0.35

    image = cv2.imread(source_image_path)
    # Detect objects and annotate the image
    detections = grounding_dino_model.predict_with_classes(
        image=image,
        classes=enhance_class_name(class_names=CLASSES),
        box_threshold=BOX_THRESHOLD,
        text_threshold=TEXT_THRESHOLD
    )

    detections.mask = segment(
        sam_predictor=sam_predictor,
        image=cv2.cvtColor(image, cv2.COLOR_BGR2RGB),
        xyxy=detections.xyxy
    )
    
    for box in detections.xyxy:
        x1, y1, x2, y2 = box
        # Extract the region of interest using bounding box coordinates
        print(y2)
        y2 = y2 + 20
        x1 = x1 - 20
        x2 = x2 + 20
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        mask = np.zeros_like(image, dtype=np.uint8)
        cv2.rectangle(mask, (x1, y1), (x2, y2), (255, 255, 255), thickness=cv2.FILLED)
    
    head_mask_path = f"{current_directory}/uploads/{str(uuid.uuid4())}.jpg"

    if y2_h < y2:
        cv2.imwrite(head_mask_path, mask)


    image_pil = Image.open(source_image_path)
    mask_pil = Image.open(hair_mask_path_2)
    prompt = "short bob hair"
    generator = torch.Generator(device="cuda").manual_seed(0)

    images = pipe(
    prompt=prompt,
    image=image_pil,
    mask_image=mask_pil,
    guidance_scale=20.0,
    num_inference_steps=20,  # steps between 15 and 30 work well for us
    strength=0.99,  # make sure to use `strength` below 1.0
    generator=generator,
    ).images[0]

   # Check and remove the first hair mask file
    if os.path.exists(hair_mask_path_1):
        os.remove(hair_mask_path_1)

    # Check and remove the second hair mask file
    if os.path.exists(hair_mask_path_2):
        os.remove(hair_mask_path_2)

    # Check and remove the head mask file
    if os.path.exists(head_mask_path):
        os.remove(head_mask_path)

    bob_hair = f"{current_directory}/uploads/{str(uuid.uuid4())}.jpg"

    images.save(bob_hair)
    # Load an image using PIL

    image2 = Image.open(source_image_path)

    # Define a transformation to convert the image to a tensor
    transform = transforms.ToTensor()

    # Apply the transformation to the image
    image_tensor = transform(image2)

    tensor_size = image_tensor.size()
    print("Size of the image tensor:", tensor_size)

    width = tensor_size[2]  # Adjust this to your preferred width
    height = tensor_size[1]

    bg = cv2.imread(bob_hair)
    bg = cv2.resize(bg,(width,height))
    cv2.imwrite(bob_hair,bg)

    return bob_hair
    
if __name__ == "__main__":
    generate_bob_hair("model_1.jpeg")