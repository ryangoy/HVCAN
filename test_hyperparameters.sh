echo Starting baseline test
python main.py --test_name=baseline --epoch=30 --sample_dir=baseline_samples --L1_lambda=100 --latent_lambda=1.0 --ssim_lambda=1.0
echo Starting l1=10 test
python main.py --test_name=l1_10 --epoch=30 --sample_dir=low_l1_samples --L1_lambda=10 --latent_lambda=1.0 --ssim_lambda=1.0
echo Starting L1=50 and ssim=5
python main.py --test_name=50_l1_5_ssim --epoch=30 --sample_dir=high_ssim_samples --L1_lambda=50 --latent_lambda=1.0 --ssim_lambda=5.0
