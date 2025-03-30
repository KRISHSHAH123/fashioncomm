import os
import torch
import pickle
import faiss
import numpy as np
from torchvision import models, transforms
from PIL import Image
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set device to GPU if available, otherwise CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def generate_feature_file(force_regenerate=False):
    """
    Generate image features and FAISS index from images in the 'media' directory.
    
    Args:
        force_regenerate (bool): If True, regenerate features even if they exist.
    """
    logger.info("Starting feature extraction process...")

    # Load pre-trained ResNet50 model and remove the final classification layer
    model = models.resnet50(pretrained=True)
    model = torch.nn.Sequential(*list(model.children())[:-1])
    model.eval().to(device)

    # Define image preprocessing transformations
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # Define paths
    image_dir = "media"
    feature_file = os.path.join(image_dir, "image_features.pkl")
    faiss_index_file = os.path.join(image_dir, "faiss_index.bin")

    # Get current image files in the directory
    current_image_paths = {
        os.path.basename(img) for img in os.listdir(image_dir)
        if img.lower().endswith((".jpg", ".png", ".jpeg"))
    }

    # Check if feature file exists and regeneration is not forced
    existing_names = set()
    if os.path.exists(feature_file) and not force_regenerate:
        try:
            with open(feature_file, "rb") as f:
                data = pickle.load(f)
                existing_names = set(data["names"])
        except Exception as e:
            logger.error(f"Error loading feature file: {e}. Regenerating...")

    # Regenerate if necessary
    if force_regenerate or current_image_paths != existing_names or not os.path.exists(feature_file):
        logger.info("Regenerating feature file...")
        image_paths = [
            os.path.join(image_dir, img).replace("\\", "/")
            for img in os.listdir(image_dir)
            if img.lower().endswith((".jpg", ".png", ".jpeg"))
        ]

        def extract_features(image_path):
            """Extract features from a single image."""
            try:
                image = Image.open(image_path).convert("RGB")
                image = transform(image).unsqueeze(0).to(device)
                with torch.no_grad():
                    feature = model(image).squeeze().cpu().numpy()
                return feature.flatten()
            except Exception as e:
                logger.error(f"Error processing {image_path}: {e}")
                return None

        # Process all images
        features, image_files, image_names = [], [], []
        for img_path in image_paths:
            feature_vector = extract_features(img_path)
            if feature_vector is not None:
                features.append(feature_vector)
                image_files.append(img_path)
                image_names.append(os.path.basename(img_path))
                logger.info(f"Processed: {img_path}")

        if not features:
            logger.warning("No valid images processed.")
            return

        # Save features to pickle file
        features_np = np.array(features, dtype=np.float32)
        with open(feature_file, "wb") as f:
            pickle.dump({"features": features_np, "paths": image_files, "names": image_names}, f)
        logger.info(f"Saved feature file at: {feature_file}")

        # Create and save FAISS index
        index = faiss.IndexFlatL2(features_np.shape[1])
        index.add(features_np)
        faiss.write_index(index, faiss_index_file)
        logger.info(f"Saved FAISS index at: {faiss_index_file}")
    else:
        logger.info("Feature file up-to-date.")

# Run feature generation if executed directly
if __name__ == "__main__":
    generate_feature_file(force_regenerate=True)
