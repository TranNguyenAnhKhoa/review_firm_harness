"""Read only the visible Antigravity conversation; never clicks approval controls."""
import asyncio
from scripts.antigravity_handoff import DesktopUI


async def main():
    async with DesktopUI() as ui:
        state = await ui.evaluate("JSON.stringify({path:location.pathname,text:document.body.innerText})")
        print(state[-22000:])


if __name__ == '__main__':
    asyncio.run(main())
