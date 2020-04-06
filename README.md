# End-to-end Recovery of Human Shape and Pose

This repository is adaptation of HMR model for our purposes, 
based on [this project](https://akanazawa.github.io/hmr/). 
Unfortunately it doesn't run out of the box due to outdated code adn dependencies and we must to rewrite 
some code and add utility methods. 

![Teaser Image](https://akanazawa.github.io/hmr/resources/images/teaser.png)

### Installation
Use this prepared Docker image:
`https://hub.docker.com/r/dawars/hmr/`

### Demo

1. Download the pre-trained models
```
wget https://people.eecs.berkeley.edu/~kanazawa/cachedir/hmr/models.tar.gz && tar -xf models.tar.gz
```

2. Run the demo
```
python -m demo --img_path data/coco1.png
python -m demo --img_path data/im1954.jpg
```

Images should be tightly cropped, where the height of the person is roughly 150px.
On images that are not tightly cropped, you can run
[openpose](https://github.com/CMU-Perceptual-Computing-Lab/openpose) and supply
its output json (run it with `--write_json` option).
When json_path is specified, the demo will compute the right scale and bbox center to run HMR:
```
python -m demo --img_path data/random.jpg --json_path data/random_keypoints.json
```
(The demo only runs on the most confident bounding box, see `src/util/openpose.py:get_bbox`)

### Training code/data
Please see the this [README](doc/train.md)!

### Citation
```
@inProceedings{kanazawaHMR18,
  title={End-to-end Recovery of Human Shape and Pose},
  author = {Angjoo Kanazawa
  and Michael J. Black
  and David W. Jacobs
  and Jitendra Malik},
  booktitle={Computer Vision and Pattern Recognition (CVPR)},
  year={2018}
}
```

 
