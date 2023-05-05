// setTimeout(function(){
//     location.reload();
// }, 5000);

const room_idx_to_pos_class = {
    "0" : "pet-living-room",
    "1" : "pet-bedroom-small",
    "2" : "pet-bedroom-large",
    "3" : "pet-bathroom",
    "-1": "pet-outside"
};

const image_id_to_pet_idx = {
    "pet0": "0",
    "pet1": "1"
};

var current_rooms = [-1, -1];

const setImagePosition = (imageId, target_room_id) => {
    const image = document.getElementById(imageId);
    const current_room_id = current_rooms[image_id_to_pet_idx[imageId]];
    image.classList.replace(room_idx_to_pos_class[current_room_id], room_idx_to_pos_class[target_room_id]);
    console.log(room_idx_to_pos_class[current_room_id], room_idx_to_pos_class[target_room_id])
    current_rooms[parseInt(image_id_to_pet_idx[imageId], 10)] = parseInt(target_room_id, 10);
}

document.addEventListener('DOMContentLoaded', () => {
    setImagePosition("pet0", data[0].room_located); // Set the position of Image 1
    setImagePosition("pet1", data[1].room_located); // Set the position of Image 2
});