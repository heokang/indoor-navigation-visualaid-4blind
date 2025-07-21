import torch
import torchvision
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor

# Load Mask R-CNN model
model = torchvision.models.detection.maskrcnn_resnet50_fpn(weights=None)
num_classes = 21

# Modify the model head
in_features = model.roi_heads.box_predictor.cls_score.in_features
model.roi_heads.box_predictor = torchvision.models.detection.faster_rcnn.FastRCNNPredictor(in_features, num_classes)

in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
hidden_layer = 256
model.roi_heads.mask_predictor = MaskRCNNPredictor(in_features_mask, hidden_layer, num_classes)

# Load model weights
model_load_path = "C:/Users/ime/capstone/capstone/walkinter/objectdetectmodel/mask_rcnn_model_real1.pth"

# Load the state dict and apply it to the model
state_dict = torch.load(model_load_path, map_location=torch.device('cpu'))
model.load_state_dict(state_dict)

# Set model to evaluation mode
model.eval()

# Device configuration
device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
model.to(device)