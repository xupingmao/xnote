@rem 人工测试


rm -rf testdata
python3 sentinel.py app.py --config config/boot/boot.test.properties

pause