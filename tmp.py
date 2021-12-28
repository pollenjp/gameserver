if __name__ == "__main__":
    import app.model
    import app.room_model

    print(f'{app.room_model.get_room_status(10)}')
    # print(f'{app.room_model.create_room(live_id=1001)}')
    # print(f"{app.room_model.get_rooms_by_live_id(2)}")
    # print(f'{app.model.update_user(token="db0f6439-3c87-4b65-86a0-7c47c136a7d8", name="pollenjp-modified", leader_card_id=2)}')
    # print(f'{app.model.update_user(token="nothing", name="pollenjp-modified", leader_card_id=2)}')
