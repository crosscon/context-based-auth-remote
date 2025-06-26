import torch
import torch.nn as nn
import torchvision.models as models

import os
import dotenv

dotenv.load_dotenv()

ML_MODEL_CHECKPOINT_PATH = os.environ.get("ML_MODEL_CHECKPOINT_PATH")

# taken from https://github.com/RS2002/CrossFi/blob/main/model.py, introduced by "CrossFi: A Cross Domain WiFi Sensing Framework Based on Siamese Network"
class ResnetBasedSiamese2dNetwork(nn.Module):
    def __init__(self, output_dims: int = 64, channel: int = 2, pretrained: bool = True, norm: bool = False):
        super().__init__()
        self.model = models.resnet18(pretrained)
        self.model.conv1 = nn.Conv2d(channel, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.model.fc = nn.Linear(self.model.fc.in_features, output_dims)
        self.norm = norm

    def forward(self,x):
        if self.norm:
            mean = torch.mean(x, dim=-1, keepdim=True)
            std = torch.std(x, dim=-1, keepdim=True)
            y = (x - mean) / std
        else:
            y = x
        return self.model(y)


class SiameseDiscriminator(nn.Module):
    def __init__(self, embedding_dim=64):
        super().__init__()
        # after concat you have 2×embedding_dim input
        self.classifier = nn.Sequential(
            nn.Linear(2 * embedding_dim, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(256, 64),
            nn.ReLU(inplace=True),
            nn.Linear(64, 1),
            nn.Sigmoid(),   # outputs P(same)
        )

    def forward(self, e1, e2):
        # you could also do torch.abs(e1 - e2) or elementwise mult
        x = torch.cat([e1, e2], dim=1)
        return self.classifier(x)


class SiameseModel(nn.Module):
    def __init__(self, embedding_dim=64):
        super().__init__()
        self.encoder = ResnetBasedSiamese2dNetwork()
        self.discriminator = SiameseDiscriminator(embedding_dim)

    def forward(self, x1, x2):
        e1 = self.encoder(x1)
        e2 = self.encoder(x2)
        p_same = self.discriminator(e1, e2)
        return p_same


def model_predict(embedding_model, csi_1, csi_2, device):
    with torch.no_grad():
        csi_1, csi_2 = csi_1.to(device), csi_2.to(device)

        p_same = embedding_model(csi_1, csi_2).flatten()
        pred = (p_same >= 0.9).float().item()

    return pred > 0



## External Func
def authenticate(csi_1, csi_2):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    embedding_model = SiameseModel().to(device).eval()

    embedding_model.load_state_dict(torch.load(ML_MODEL_CHECKPOINT_PATH, map_location=device))

    return model_predict(embedding_model, csi_1, csi_2, device)
