# hypixelbot
A silly litte project to learn about API's and discord interactions

## What is it?
> It is a simple yet efficient, caching discord bot for purposes such as finding players, checking auction house and more!

## Will I scale it?
> No. If there is a issue do make a [GitHub issue](https://github.com/outraft/hypixelbot/issues/new) about it but I might **NOT** fix it - no promises here!

## How can I run the bot?

Firstly, thank you for giving my bot a chance! :shipit:
Let me show you the steps!
1. Install the folders to a convinient place.
2. Run the command `pip install -r requirements.txt` at **the file location** - do not play dumb.
3. Add a `.env` file and add these:

   ```env
   TOKEN = your discord API token (secret) here
   MONGO = your (hopefully MongoDB) connection link here
    ```

5. Run the `main.py` file. You will see in the command line that "x amount of global commands are synced", and "Logged on as: y" (x and y are changing variables)
That is it! Run the commands whenever and however you like!

## What commands should I know?
> I might have forgotten /help command...

/ah -> General information for auction house, shows all auctions.
/dah -> A specific auction show-er, need one of the following:
  Profile UUID
  Auction UUID
  Player UUID
/news -> Skyblock news.
/mayor -> Mayor and/or election data.
> Might add more, might not.
Anyways, since you read all of this nonsense here is a picture of a car (not mine)
![Fake car!](https://i.imgur.com/6FBBzb9.png)
![Real car!](https://www.wondercide.com/cdn/shop/articles/Upside_down_gray_cat.png?v=1685551065)
