function accessMetrics(type) {
    axios.post('/api/metrics?type=' + type)
        .then(function (response) {
            // console.log(response);
        })
        .catch(function (error) {
            // console.log(error);
        });
}