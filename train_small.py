import tensorflow as tf
from tensorflow.keras.losses import cosine_proximity, categorical_crossentropy
from tensorflow.keras.optimizers import SGD, Adam
from tensorflow.keras.callbacks import LearningRateScheduler, EarlyStopping, ModelCheckpoint
from tensorflow.keras.callbacks import TensorBoard

import math
import os
import argparse

from scipy.spatial.distance import cosine

from dataloader import *
from models import *
from utility import *

from tensorflow.keras.backend import set_session

gpu_config = tf.ConfigProto()
gpu_config.gpu_options.allow_growth = True
set_session(tf.Session(config=gpu_config))

#################################################### parameters ##########################################################

if not files_exist():
    look_ups()


if not os.listdir(str(os.path.dirname(os.path.abspath(__file__))) +'/data/glove_data'):
    print('Download the GloVe embeddings from the webpage first!')

if not len(os.listdir('/ssd_scratch/cvit/anirudhkaushik/subject/'))==15:
    print('Download the fMRI data from all the subjects from the webpage first!')

parser = argparse.ArgumentParser()
parser.add_argument('-subject', type = str, default = 'M15')
parser.add_argument('-class_model', type= int, default = 1)
args = parser.parse_args()

subject = args.subject

save_file =str(os.path.dirname(os.path.abspath(__file__)))+'/model_weights/Subject' +subject+'_small_model.h5'

#Glove prediction model or classifiction model:
class_model = args.subject
if class_model:
    class_weight = 1.0
    glove_weight = 0.0

else:
    class_weight = 0.0
    glove_weight = 1.0



#################################################### data load ##########################################################

data_train, data_test, glove_train, glove_test, data_fine, data_fine_test, glove_fine, glove_fine_test = dataloader_sentence_word_split_new_matching_all_subjects(subject)

class_fine_test =np.eye(180)
class_fine = np.reshape(np.tile(class_fine_test,(42,1)),(7560,180))
class_fine_test = np.reshape(np.tile(class_fine_test,(3,1)),(540,180)) 
class_train = np.zeros((4530,180))

#################################################### losses & schedule ##########################################################

initial_lrate = 0.001
epochs_drop = 10.0  
epochs=100
batch_size= 180

def step_decay(epoch):

   drop = 0.3       
   lrate = initial_lrate * math.pow(drop,
           math.floor((1+epoch)/epochs_drop))
   return lrate

def mean_distance_loss(y_true, y_pred):
    total = 0
    total_two = 0
    
    val = 179
    for i in range((val+1)):
        if i == 0:
            total += (val*cosine_proximity(y_true,y_pred))
        else:
            rolled = tf.manip.roll(y_pred, i, axis=0)
            total_two -= cosine_proximity(y_true,rolled)
    return total_two/val + total/val

#################################################### model ##########################################################
optimizer = Adam(lr=1e-3,amsgrad=True) 

model = encdec_small_model()
model.compile(loss= {'pred_glove':mean_distance_loss,'pred_class':categorical_crossentropy},loss_weights=[glove_weight,class_weight],optimizer=optimizer, metrics=['accuracy']) 

##################################################### callbacks ########################################################
callback_list = []

if class_model:
    reduce_lr = LearningRateScheduler(step_decay)
    callback_list.append(reduce_lr)
    early = EarlyStopping(monitor= 'val_pred_class_loss', patience=10)
    callback_list.append(early)
    model_checkpoint_callback = ModelCheckpoint(filepath=save_file,save_weights_only=True,monitor='val_pred_class_acc',mode='max',save_best_only=True)
    callback_list.append(model_checkpoint_callback)
else:
    reduce_lr = LearningRateScheduler(step_decay)
    callback_list.append(reduce_lr)
    early = EarlyStopping(monitor= 'val_pred_glove_loss', patience=10)
    callback_list.append(early)
    model_checkpoint_callback = ModelCheckpoint(filepath=save_file,save_weights_only=True,monitor='val_pred_glove_loss',mode='min',save_best_only=True)
    callback_list.append(model_checkpoint_callback)
##################################################### fit & save #######################################################

model.fit([data_fine], [glove_fine,class_fine], batch_size=batch_size, epochs=epochs, verbose=2, callbacks=callback_list, validation_data=([data_fine_test], [glove_fine_test,class_fine_test]))  
model.load_weights(save_file)

##################################################### Evaluation #######################################################

glove_pred_test, pred_class = model.predict(data_fine_test)

text_all = open(str(os.path.dirname(os.path.abspath(__file__))) + "/results/Subject" +subject+"_small_model.txt", "a+")

if class_model:
    accuracy, accuracy_five, accuracy_ten = top_5(pred_class,class_fine_test)

    text_all.write('Accuracy_top1: ' + str(accuracy) + ' Accuracy_top5: ' + str(accuracy_five) + 'Accuracy_top10: ' + str(accuracy_ten))
    text_all.write('\n')

else:
    accuracy_test = np.zeros((3))

    accuracy_test[0] = evaluation(glove_pred_test[:180,:],glove_fine_test[:180,:])

    accuracy_test[1] = evaluation(glove_pred_test[180:360,:],glove_fine_test[180:360,:])

    accuracy_test[2] = evaluation(glove_pred_test[360:,:],glove_fine_test[360:,:])


    text_all.write('Pairwise Accuracy: ' + str(np.mean(accuracy_test)))
    text_all.write('\n')

text_all.close()