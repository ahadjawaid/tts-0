# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/06-tts-data.ipynb.

# %% auto 0
__all__ = ['TTSDataset', 'collate_fn']

# %% ../nbs/06-tts-data.ipynb 2
import torch
from torch.utils.data import Dataset, DataLoader
from fastspeech.loading import *
from fastspeech.preprocess import *
from torch import tensor
import fastcore.all as fc
from functools import partial
from tqdm.auto import tqdm

# %% ../nbs/06-tts-data.ipynb 6
class TTSDataset(Dataset):
    def __init__(self, 
                 path_data: str,
                 path_vocab: str,
                 sr: int = 22050,
                 n_fft: int = 1024,
                 hl: int = 256,
                 nb: int = 80,
                ) -> None:
        super().__init__()
        replace_to_tg = partial(replace_extension, extension=".TextGrid")
        
        files = get_audio_files(path_data)
        files_tg = files.map(replace_to_tg)
        
        self.vocab = Vocab(path_vocab, ["spn"])
        
        self.data = []
        for audio_file, tg_file in tqdm(list(zip(files, files_tg))):
            wav = load_audio(audio_file, sr=sr)
            mel = melspectrogram(wav, n_fft=n_fft, hl=hl, nb=nb)
            phones, duration = get_phones_and_durations(tg_file, sr, hl)
            
            phones = tensor(phones_list_to_num(phones, self.vocab)).squeeze()
            mels = tensor(melspectrogram(wav, n_fft, hl, nb))
            durations = round_and_align_durations(tensor(duration), mels.shape[-1]).to(torch.int)
            
            self.data.append((phones, durations, mels))
            
    def __getitem__(self, index: int) -> tuple:
        return self.data[index]
    
    def __len__(self) -> int:
        return len(self.data)

# %% ../nbs/06-tts-data.ipynb 9
def collate_fn(inp, pad_num: int):
    phones, durations, mels = [item[0] for item in inp], [item[1] for item in inp], [item[2] for item in inp]
    
    mel_attention = tensor(list(map(lambda t: t.shape[-1], mels)))
    phones_attention = tensor(list(map(lambda t: t.shape[-1], phones)))
    
    mel_batched = pad_mels(mels, 0)
    phones_batched = pad_phones(pad_max_seq(phones), pad_num)
    mel_len = mel_batched.shape[-1]
    
    duration_batched = pad_duration(pad_max_seq(durations), mel_batched.shape[-1])
    
    assert phones_batched.shape == duration_batched.shape
    assert len(duration_batched.sum(dim=1).unique()) == 1
    
    return phones_batched, duration_batched, mel_batched, mel_attention, phones_attention
