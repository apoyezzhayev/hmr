"""
Demo of HMR.

Note that HMR requires the bounding box of the person in the image. The best performance is obtained when max length of the person in the image is roughly 150px. 

When only the image path is supplied, it assumes that the image is centered on a person whose length is roughly 150px.
Alternatively, you can supply output of the openpose to figure out the bbox and the right scale factor.

Sample usage:

# On images on a tightly cropped image around the person
python -m demo --img_path data/im1963.jpg
python -m demo --img_path data/coco1.png

# On images, with openpose output
python -m demo --img_path data/random.jpg --json_path data/random_keypoints.json
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import glob
import os
import sys

import matplotlib

matplotlib.use('Agg')

import numpy as np
import pandas as pd
import skimage.io as io
import tensorflow as tf
from absl import flags
import pickle

from tqdm.autonotebook import tqdm

import src.config
from src.RunModel import RunModel
from src.util import image as img_util
from src.util import openpose as op_util
from src.util import renderer as vis_util
from pathlib2 import Path

flags.DEFINE_string('img_path', 'data/im1963.jpg', 'Image to run')
flags.DEFINE_string(
    'json_path', None,
    'If specified, uses the openpose output to crop the image.')


def visualize(img_path, img, proc_param, joints, verts, cam, output):
    """
    Renders the result in original image coordinate frame.
    """
    cam_for_render, vert_shifted, joints_orig = vis_util.get_original(
        proc_param, verts, cam, joints, img_size=img.shape[:2])

    # Render results
    skel_img = vis_util.draw_skeleton(img, joints_orig)
    # TODO: add alpha to avatar
    rend_img_overlay = renderer(
        vert_shifted, cam=cam_for_render, img=skel_img, do_alpha=True)
    # rend_img_overlay = vis_util.draw_skeleton(rend_img_overlay, joints_orig)
    rend_img = renderer(
        vert_shifted, cam=cam_for_render, img_size=img.shape[:2])
    rend_img_vp1 = renderer.rotated(
        vert_shifted, 60, cam=cam_for_render, img_size=img.shape[:2])
    rend_img_vp2 = renderer.rotated(
        vert_shifted, -60, cam=cam_for_render, img_size=img.shape[:2])

    import matplotlib.pyplot as plt
    # plt.ion()
    plt.figure(1, figsize=(10, 10))
    plt.clf()
    plt.subplot(231)
    plt.imshow(img)
    plt.title('input')
    plt.axis('off')
    plt.subplot(232)
    plt.imshow(skel_img)
    plt.title('joint projection')
    plt.axis('off')
    plt.subplot(233)
    plt.imshow(rend_img_overlay)
    plt.title('3D Mesh overlay')
    plt.axis('off')
    plt.subplot(234)
    plt.imshow(rend_img)
    plt.title('3D mesh')
    plt.axis('off')
    plt.subplot(235)
    plt.imshow(rend_img_vp1)
    plt.title('diff vp')
    plt.axis('off')
    plt.subplot(236)
    plt.imshow(rend_img_vp2)
    plt.title('diff vp')
    plt.axis('off')
    plt.draw()
    print('saving to %s' % output)
    plt.savefig(os.path.join(output, os.path.splitext(os.path.basename(img_path))[0] + ".png"))
    io.imsave(os.path.join(output, os.path.splitext(os.path.basename(img_path))[0] + "_big.png"), rend_img_overlay)  # rend_img[:,:,:3])#
    # import ipdb
    # ipdb.set_trace()


def preprocess_image(img_path, json_path=None):
    img = io.imread(img_path)
    if img.shape[2] == 4:
        img = img[:, :, :3]

    if json_path is None:
        if np.max(img.shape[:2]) != config.img_size:
            print('Resizing so the max image size is %d..' % config.img_size)
            scale = (float(config.img_size) / np.max(img.shape[:2]))
        else:
            scale = 1.
        center = np.round(np.array(img.shape[:2]) / 2).astype(int)
        # image center in (x,y)
        center = center[::-1]
    else:
        scale, center = op_util.get_bbox(json_path)

    crop, proc_param = img_util.scale_and_crop(img, scale, center,
                                               config.img_size)

    # Normalize image to [-1, 1]
    crop = 2 * ((crop / 255.) - 0.5)

    return crop, proc_param, img


def out_name(out_dir, img_path, suffix=''):
    shop_name = img_path.parent.name
    out_path = os.path.join(str(out_dir), str(shop_name), str(img_path.with_suffix('').name + suffix))
    if not os.path.exists(out_path):
        Path(out_path).parent.mkdir(exist_ok=True, parents=True)
    # print(out_dir, shop_name, img_path.with_suffix('').name + suffix)
    return out_path


def main(img_path, json_path=None, out_dir="hmr/output"):
    if config.img_path.endswith('.csv'):
        csv = pd.read_csv(config.img_path)
    else:
        raise NotImplementedError

    sess = tf.Session()
    model = RunModel(config, sess=sess)

    for ind, item in tqdm(csv.iterrows(), desc='Creating avatars'):
        tqdm.write('Creating avatar for %s' % item.img_path)
        out_dir = Path(out_dir)
        img_path = Path(item.img_path)
        json_path = Path(item.annot_path)
        dump_path = out_name(out_dir, img_path, suffix='_verts.pkl')

        if Path(dump_path).exists():
            tqdm.write('Avatar is already created')
            continue

        input_img, proc_param, img = preprocess_image(img_path, str(json_path))
        # Add batch dimension: 1 x D x D x 3
        input_img = np.expand_dims(input_img, 0)

        joints, verts, cams, joints3d, theta = model.predict(
            input_img, get_theta=True)

        # Write outputs
        joints_csv = os.path.join(str(out_dir), "csv/", os.path.splitext(os.path.basename(str(img_path)))[0] + ".csv")
        export_joints(joints3d, joints_csv)
        #     pose = pd.DataFrame(theta[:, 3:75])

        #     pose.to_csv("hmr/output/theta_test.csv", header=None, index=None)

        #     print('THETA:', pose.shape, pose)

        #     import cv2
        #     rotations = [cv2.Rodrigues(aa)[0] for aa in pose.reshape(-1, 3)]
        #     print('ROTATIONS:', rotations)
        out_images_dir = os.path.join(str(out_dir), "images")

        # measure(theta[0][0], verts[0][0])  # view, batch

        # Write avatar
        with open(str(dump_path), 'wb') as f:
            tqdm.write('Vertices dump was written to %s' % dump_path)
            pickle.dump(verts, f)

        visualize(str(img_path), img, proc_param, joints[0], verts[0], cams[0], output=str(out_images_dir))

def export_joints(joints3d, file):
    joints_names = ['Ankle.R_x', 'Ankle.R_y', 'Ankle.R_z',
                    'Knee.R_x', 'Knee.R_y', 'Knee.R_z',
                    'Hip.R_x', 'Hip.R_y', 'Hip.R_z',
                    'Hip.L_x', 'Hip.L_y', 'Hip.L_z',
                    'Knee.L_x', 'Knee.L_y', 'Knee.L_z',
                    'Ankle.L_x', 'Ankle.L_y', 'Ankle.L_z',
                    'Wrist.R_x', 'Wrist.R_y', 'Wrist.R_z',
                    'Elbow.R_x', 'Elbow.R_y', 'Elbow.R_z',
                    'Shoulder.R_x', 'Shoulder.R_y', 'Shoulder.R_z',
                    'Shoulder.L_x', 'Shoulder.L_y', 'Shoulder.L_z',
                    'Elbow.L_x', 'Elbow.L_y', 'Elbow.L_z',
                    'Wrist.L_x', 'Wrist.L_y', 'Wrist.L_z',
                    'Neck_x', 'Neck_y', 'Neck_z',
                    'Head_x', 'Head_y', 'Head_z',
                    'Nose_x', 'Nose_y', 'Nose_z',
                    'Eye.L_x', 'Eye.L_y', 'Eye.L_z',
                    'Eye.R_x', 'Eye.R_y', 'Eye.R_z',
                    'Ear.L_x', 'Ear.L_y', 'Ear.L_z',
                    'Ear.R_x', 'Ear.R_y', 'Ear.R_z']

    joints_export = pd.DataFrame(joints3d.reshape(1, 57), columns=joints_names)
    joints_export.index.name = 'frame'

    joints_export.iloc[:, 1::3] = joints_export.iloc[:, 1::3] * -1
    joints_export.iloc[:, 2::3] = joints_export.iloc[:, 2::3] * -1
    hipCenter = joints_export.loc[:][['Hip.R_x', 'Hip.R_y', 'Hip.R_z',
                                      'Hip.L_x', 'Hip.L_y', 'Hip.L_z']]

    joints_export['hip.Center_x'] = hipCenter.iloc[0][::3].sum() / 2
    joints_export['hip.Center_y'] = hipCenter.iloc[0][1::3].sum() / 2
    joints_export['hip.Center_z'] = hipCenter.iloc[0][2::3].sum() / 2

    joints_export.to_csv(file)

def join_csv(csv_dir, csv_joined_dir):
    all_files = glob.glob(os.path.join(csv_dir, "*.csv"))
    all_files.sort(key=lambda x: x.split('/')[-1].split('.')[0])
    df_from_each_file = (pd.read_csv(f) for f in all_files)
    concatenated_df = pd.concat(df_from_each_file, ignore_index=True)

    concatenated_df['frame'] = concatenated_df.index + 1
    concatenated_df.to_csv(os.path.join(csv_joined_dir, "csv_joined.csv"), index=False)


if __name__ == '__main__':
    config = flags.FLAGS
    config(sys.argv)

    out_dir = Path(config.out_dir)
    csv_dir = out_dir / 'csv'
    csv_joined = out_dir / 'csv_joined'
    img_dir = out_dir / 'images'
    csv_dir.mkdir(parents=True, exist_ok=True)
    csv_joined.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    # Using pre-trained model, change this to use your own.
    config.load_path = src.config.PRETRAINED_MODEL

    config.batch_size = 1

    renderer = vis_util.SMPLRenderer(face_path=config.smpl_face_path)
    print(out_dir)
    main(config.img_path, config.json_path, str(out_dir))

    join_csv(str(csv_dir), str(csv_joined))
