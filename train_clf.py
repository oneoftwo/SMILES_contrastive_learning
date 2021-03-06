import numpy as np
import random
import pickle
from copy import deepcopy
from rdkit import Chem
import torch 
from torch import optim 
from torch import nn
from tqdm import tqdm
from torch.utils.data import DataLoader
from rdkit import RDLogger
RDLogger.DisableLog('rdApp.*')

from _dataset import SMILESDataset, seq_collate_fn
from _model import SiamClf, SMILESSiam, LanguageModel
import _train as TRAIN
import _argument as ARGUMENT
from util.sys.sys import set_cuda_visible_devices


def main(args):
    
    print('\ntrain_clf.py\n')
    print('#' * 80 + '\n')
    
    set_cuda_visible_devices(is_print=True, ngpus=1)
    print()

    # args = ARGUMENT.get_train_clf_args()
    
    for x in vars(args):
        print(f'{x}: {vars(args)[x]}')
    print()

    # load
    data_fn = args.data_fn 
    sample_list = pickle.load(open(data_fn, 'rb'))
    random.shuffle(sample_list)
    
    print(f'total loaded data: {len(sample_list)}')

    ori_c_to_i = pickle.load(open('./data/c_to_i.pkl', 'rb'))
    train_set = SMILESDataset(sample_list[:int(len(sample_list) * 0.8)], ori_c_to_i, is_target=True)
    valid_set = SMILESDataset(sample_list[int(len(sample_list) * 0.8):], ori_c_to_i, is_target=True)
    c_to_i = train_set.c_to_i
    
    print(f'train data: {len(train_set)}\nval data: {len(valid_set)}')
    print(f'positive data: {len([x for x in valid_set if x["target"] == 1])}')
    print(f'negative data: {len([x for x in valid_set if x["target"] == 0])}\n')
    print(c_to_i, '\n')

    siam_model_state_dict_fn = args.siam_model_fn
    representation_model = LanguageModel(n_char=len(c_to_i), hid_dim=args.hid_dim, n_layer=args.n_layer)
    siam_model = SMILESSiam(representation_model, use_pp_prediction=args.use_pp_prediction)
    siam_model.load_state_dict(torch.load(siam_model_state_dict_fn))
    clf_model = SiamClf(siam_model)

    print(f'{clf_model}\n')
    print(f"|{'epoch':^8}|" + 
            f"{'train_loss':^12}|" + 
            f"{'val_loss':^12}|" + 
            f"{'accuracy':^12}|" +
            f"{'precision':^12}|" +
            f"{'recall':^12}|" + 
            f"{'auc_roc':^12}|" + 
            f"{'auc_prc':^12}|" + 
            f"{'time':^12}|")
    
    train_loader = DataLoader(train_set, batch_size=args.bs, shuffle=True, \
            collate_fn=seq_collate_fn, num_workers=8, drop_last=True)
    val_loader = DataLoader(valid_set, batch_size=128, shuffle=False, \
            collate_fn=seq_collate_fn, num_workers=8, drop_last=True)

    # train, validate
    lr = args.lr
    best_val_loss = 1e10
    
    # clf_model = nn.DataParallel(clf_model, device_ids=[0, 1, 2])
    for epoch in range(1, args.n_epoch + 1):
        optimizer = optim.Adam(clf_model.parameters(), lr=lr)
        clf_model, train_result = \
                TRAIN.process_clf(clf_model, train_loader, optimizer=optimizer)
        # _, val_result = TRAIN.process_clf(clf_model, val_loader)
        _, val_result = TRAIN.process_clf_validation_smiles_enumerate(clf_model, val_loader, n_trial=8)
        lr = lr * args.lr_decay
        
        if val_result['loss'] < best_val_loss:
            best_result = val_result
            best_val_loss = val_result['loss']
            marker = '*'
            tol = 0
        else:
            marker = ''
            tol += 1

        print(f"|{epoch:^8}|" + 
                f"{train_result['loss']:^12.4f}|" + 
                f"{val_result['loss']:^12.4f}|" + 
                f"{val_result['accuracy']:^12.2f}|" +
                f"{val_result['precision']:^12.2f}|" +
                f"{val_result['recall']:^12.2f}|" + 
                f"{val_result['auc_roc']:^12.4f}|" + 
                f"{val_result['auc_prc']:^12.4f}|" + 
                f"{train_result['time']+val_result['time']:^12.2f}|" + 
                f"{marker}")
        
        if tol > 30:
            print('early stop')
            break
    
    print('\n best result')
    print(best_result)
    
    torch.cuda.empty_cache()

    return best_result

    
if __name__ == '__main__':
    args = ARGUMENT.get_train_clf_args()
    main(args)

