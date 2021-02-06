function accessMetrics() {
    axios.post('/api/metrics')
        .then(function (response) {
            // console.log(response);
        })
        .catch(function (error) {
            // console.log(error);
        });
}