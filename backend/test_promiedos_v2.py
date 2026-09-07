import esd

def main():
    client = esd.PromiedosClient()

    for date_option in ["today", "yesterday"]:
        print(f"\n--- Probando date='{date_option}' ---")
        try:
            events = client.get_events(date=date_option)
            print(f"Total de eventos encontrados: {len(events)}")
            if events:
                print(events[0])
        except Exception as ex:
            print(f"ERROR: {type(ex).__name__}: {ex}")


if __name__ == "__main__":
    main()