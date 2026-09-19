from __future__ import annotations
import torch
from torch import nn

class MLP(nn.Module):
    implementation_id = "PYTORCH_MLP_V1"
    framework = "pytorch"
    def __init__(self,input_size,hidden=(64,32),dropout=.1):
        super().__init__(); self.net=nn.Sequential(nn.Linear(input_size,hidden[0]),nn.ReLU(),nn.Dropout(dropout),nn.Linear(hidden[0],hidden[1]),nn.ReLU(),nn.Linear(hidden[1],1))
    def forward(self,x): return self.net(x).squeeze(-1)

class Recurrent(nn.Module):
    def __init__(self,kind,input_size,hidden_size=32):
        super().__init__(); self.rnn=(nn.LSTM if kind=='lstm' else nn.GRU)(input_size,hidden_size,batch_first=True); self.head=nn.Linear(hidden_size+6,1)
    def forward(self,x,future_calendar):
        _,state=self.rnn(x); h=state[0][-1] if isinstance(state,tuple) else state[-1]
        return self.head(torch.cat([h,future_calendar],1)).squeeze(-1)

def parameter_count(model): return sum(p.numel() for p in model.parameters() if p.requires_grad)
