setTimeout(function(){
    location.reload();
}, 5000);

const room_idx_to_pos_class = {
    "0" : "pet-living-room",
    "1" : "pet-bedroom-small",
    "2" : "pet-bedroom-large",
    "3" : "pet-bathroom",
    "-1": "pet-outside"
};

const room_idx_to_room_name = {
    "0" : "Living Room",
    "1" : "Small Bedroom",
    "2" : "Large Bedroom",
    "3" : "Bathroom",
    "4" : "Outside"
};

const room_colors = [
    '#EAE7DC', // Living Room (Light Beige)
    '#BDC3C7', // Small Bedroom (Light Gray)
    '#AF7AC5', // Large Bedroom (Soft Purple)
    '#D4EFDF', // Bathroom (Mint Green)
    '#F7DC6F'  // Outside (Soft Yellow)
];

const image_id_to_pet_idx = {
    "pet0": "0",
    "pet1": "1"
};

var current_rooms = [-1, -1];

const setImagePosition = (imageId, target_room_id) => {
    const image = document.getElementById(imageId);
    const current_room_id = current_rooms[image_id_to_pet_idx[imageId]];
    image.classList.replace(room_idx_to_pos_class[current_room_id], room_idx_to_pos_class[target_room_id]);
    if (current_rooms[0] == current_rooms[1]) {
        document.getElementById("pet0").classList.remove("image-container-left");
        document.getElementById("pet1").classList.remove("image-container-right");
    } else {
        document.getElementById("pet0").classList.remove("image-container-middle");
        document.getElementById("pet1").classList.remove("image-container-middle");
    }
    current_rooms[parseInt(image_id_to_pet_idx[imageId], 10)] = parseInt(target_room_id, 10);
    if (current_rooms[0] == current_rooms[1]) {
        document.getElementById("pet0").classList.add("image-container-left");
        document.getElementById("pet1").classList.add("image-container-right");
    } else {
        document.getElementById("pet0").classList.add("image-container-middle");
        document.getElementById("pet1").classList.add("image-container-middle");
    }
}

function createPieChart(chartId, data) {
    const ctx = document.getElementById(chartId).getContext('2d');
    console.log(chartId, data)
    const chart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.map((_, i) => `${room_idx_to_room_name[i]}`),
            datasets: [
                {
                    data: data,
                    backgroundColor: room_colors,
                    borderWidth: 0
                },
            ],
        },
        options: {
            plugins: {
                legend: {
                    display: false
                },
                customBorder: {
                    borderWidth: 5
                }
            },
            animation: {
                duration: 1
            },

        },
        plugins: [{
            id: 'customBorder',
            afterDraw: function (chart, args, options) {
                const ctx = chart.ctx;
                const radius = chart.width / 2 - options.borderWidth / 2;
                const center = {
                x: chart.width / 2,
                y: chart.height / 2
            };
        
            ctx.beginPath();
            ctx.arc(center.x, center.y, radius, 0, 2 * Math.PI);
            ctx.lineWidth = options.borderWidth;
            ctx.strokeStyle = options.borderColor;
            ctx.stroke();
            }
        }]
    });
    if (chartId == "pie-chart0") {
        chart.options.plugins.customBorder.borderColor = "#fde999";
    } else {
        chart.options.plugins.customBorder.borderColor = "rgb(141, 204, 165)";
    }
}


document.addEventListener('DOMContentLoaded', () => {
    setImagePosition("pet0", data[0].room_located);
    setImagePosition("pet1", data[1].room_located);
    createPieChart("pie-chart0", data[0].time_spent_percentage)
    createPieChart("pie-chart1", data[1].time_spent_percentage)
});
