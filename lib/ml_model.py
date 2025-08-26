import torch
import torch.nn as nn
import torchvision.models as models

import os
import dotenv

dotenv.load_dotenv()

ML_MODEL_CHECKPOINT_PATH = os.environ.get("ML_MODEL_CHECKPOINT_PATH")

class CNNEmbedder(nn.Module):
    def __init__(self, channel: int = 1):
        super().__init__()
        self.model = torch.nn.Sequential(
            nn.Conv2d(channel, 4, kernel_size=3, stride=1), 
            nn.Tanh(),
            nn.Dropout2d(p=0.5),
      
            nn.Conv2d(4, 8, kernel_size=3, stride=1), 
            nn.Tanh(),
            nn.Dropout2d(p=0.5),

            nn.MaxPool2d(kernel_size=3, stride=1),

            nn.Conv2d(8, 16, kernel_size=5, stride=1), 
            nn.Tanh(),
            nn.Dropout2d(p=0.5),

            nn.Conv2d(16, 32, kernel_size=3, stride=1),
            nn.Tanh(),
            nn.AdaptiveAvgPool2d(1),

            nn.Flatten(),
        )

    def forward(self,x):
        return self.model(x)


class SiameseDiscriminator(nn.Module):
    def __init__(self):
        super().__init__()
        self.classifier = nn.Sequential(
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(self, e1, e2):
        x = torch.abs(e1 - e2)
        return self.classifier(x)


class SiameseModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = CNNEmbedder()
        self.discriminator = SiameseDiscriminator()

    def forward(self, x1, x2):
        e1 = self.encoder(x1)
        e2 = self.encoder(x2)
        p_same = self.discriminator(e1, e2)
        return p_same


def model_predict(embedding_model, csi_1, csi_2, device):
    with torch.no_grad():
        csi_1, csi_2 = csi_1.to(device), csi_2.to(device)

        p_same = embedding_model(csi_1, csi_2).flatten()
        pred = (p_same > 0.7).float().item()

    return pred > 0



## External Func
def authenticate(csi_1, csi_2):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    embedding_model = SiameseModel().to(device).eval()

    embedding_model.load_state_dict(torch.load(ML_MODEL_CHECKPOINT_PATH, map_location=device))

    return model_predict(embedding_model, csi_1, csi_2, device)