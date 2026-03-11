def test_s3_put_get(s3_client):
    bucket = "test-bucket"
    s3_client.create_bucket(Bucket=bucket)
    s3_client.put_object(Bucket=bucket, Key="hello.txt", Body=b"hello world")
    res = s3_client.get_object(Bucket=bucket, Key="hello.txt")
    data = res["Body"].read()
    assert data == b"hello world"
