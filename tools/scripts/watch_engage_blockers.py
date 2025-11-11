#!/usr/bin/env python3
import argparse
import json
import time

import cereal.messaging as messaging
from cereal import log


def main():
  parser = argparse.ArgumentParser(description="Watch engage blockers (NO_ENTRY) and engageable flag")
  parser.add_argument("--hz", type=float, default=10.0, help="Print rate in Hz")
  parser.add_argument("--once", action="store_true", help="Print one line and exit when it changes")
  parser.add_argument("--ip", type=str, default="127.0.0.1", help="ZMQ address (device IP) when running remotely")
  parser.add_argument("--show-carcontrol", action="store_true", help="Also print carControl when it changes")
  parser.add_argument("--show-liveparams", action="store_true", help="Also print liveParameters when it changes")
  parser.add_argument("--show-carstate", action="store_true", help="Also print carState when it changes")
  parser.add_argument("--show-panda", action="store_true", help="Also print pandaStates when it changes")
  parser.add_argument("--show-health", action="store_true", help="Also print manager/device/model/controls when they change")
  parser.add_argument("--show-can", action="store_true", help="Also print raw CAN messages (bus, addr, data)")
  parser.add_argument("--show-sendcan", action="store_true", help="Also print messages published by carcontroller.py (sendcan topic)")
  parser.add_argument("--json", action="store_true", help="Print states as compact JSON instead of pretty text")
  args = parser.parse_args()

  event_name_by_value = {v: k for k, v in log.OnroadEvent.EventName.schema.enumerants.items()}
  def enum_to_name(enum_val):
    try:
      return event_name_by_value[int(enum_val)]
    except Exception:
      return str(enum_val)

  def capnp_to_dict(msg):
    try:
      if msg is None:
        return None
      if hasattr(msg, 'to_dict'):
        return msg.to_dict()
      if hasattr(msg, 'as_reader') and hasattr(msg.as_reader(), 'to_dict'):
        return msg.as_reader().to_dict()
      return str(msg)
    except Exception:
      return "<unserializable>"

  def print_state(label, payload, prev_cache, as_json):
    try:
      if as_json:
        out = json.dumps(payload, sort_keys=True, separators=(",", ":"))
      else:
        out = f"{label}: " + json.dumps(payload, sort_keys=True, indent=2)
    except Exception:
      out = f"{label}: {payload}"
    if out != prev_cache:
      print(out)
      return out
    return prev_cache

  # Base topics
  services = ["onroadEvents", "selfdriveState", "liveParameters"]
  if args.show_carcontrol:
    services.append("carControl")
  if args.show_carstate:
    services.append("carState")
  if args.show_panda:
    services.append("pandaStates")
  if args.show_health:
    services += ["managerState", "deviceState", "modelV2", "controlsState"]
  if args.show_can:
    services.append("can")
  if args.show_sendcan:
    services.append("sendcan")

  sm = messaging.SubMaster(services, addr=args.ip)

  prev = None
  prev_lp = prev_cc = prev_cs = prev_ps = None
  prev_health_mgr = prev_health_dev = prev_health_mdl = prev_health_ctrls = None
  interval_s = 1.0 / max(1e-3, args.hz)

  print("Watching NO_ENTRY reasons... (Ctrl-C to stop)")
  try:
    while True:
      sm.update(int(interval_s * 1000))

      # ----------- engage / NO_ENTRY section -----------
      no_entry_events = [enum_to_name(e.name) for e in sm["onroadEvents"] if e.noEntry]
      sds = capnp_to_dict(sm["selfdriveState"]) if sm.seen["selfdriveState"] else None
      cur_payload = {"NO_ENTRY": no_entry_events, "selfdriveState": sds}
      cur_blob = json.dumps(cur_payload, sort_keys=True, separators=(",", ":"))
      if cur_blob != prev:
        prev = print_state("engage", cur_payload, prev, args.json)
        if args.once:
          break

      # ----------- liveParameters -----------
      if args.show_liveparams and sm.seen["liveParameters"]:
        lp_payload = capnp_to_dict(sm["liveParameters"])
        lp_blob = json.dumps(lp_payload, sort_keys=True, separators=(",", ":"))
        if lp_blob != prev_lp:
          prev_lp = print_state("liveParameters", lp_payload, prev_lp, args.json)

      # ----------- show CAN (RX from Panda) -----------
      if args.show_can and sm.seen.get("can", False):
        for msg in sm["can"]:
          try:
            print(f"CAN RX bus {msg.src}: 0x{msg.address:X} [{len(msg.dat)}] {msg.dat.hex()}")
          except Exception:
            print(f"CAN RX message: {msg}")

      # ----------- show sendcan (TX from CarController) -----------
      if args.show_sendcan and sm.seen.get("sendcan", False):
        for msg in sm["sendcan"]:
          try:
            print(f"CAN TX bus {msg.src}: 0x{msg.address:X} [{len(msg.dat)}] {msg.dat.hex()}")
          except Exception:
            print(f"CAN TX message: {msg}")

      # ----------- pandaStates -----------
      if args.show_panda and sm.seen.get("pandaStates", False):
        pandas = [capnp_to_dict(ps) for ps in sm["pandaStates"]]
        prev_ps = print_state("pandaStates", pandas, prev_ps, args.json)

      # ----------- carControl -----------
      if args.show_carcontrol and sm.seen.get("carControl", False):
        cc_payload = capnp_to_dict(sm["carControl"])
        prev_cc = print_state("carControl", cc_payload, prev_cc, args.json)

      # ----------- carState -----------
      if args.show_carstate and sm.seen.get("carState", False):
        cs_payload = capnp_to_dict(sm["carState"])
        prev_cs = print_state("carState", cs_payload, prev_cs, args.json)

      # ----------- health/status topics -----------
      if args.show_health:
        if sm.seen.get("managerState", False):
          prev_health_mgr = print_state("managerState", capnp_to_dict(sm["managerState"]), prev_health_mgr, args.json)
        if sm.seen.get("deviceState", False):
          prev_health_dev = print_state("deviceState", capnp_to_dict(sm["deviceState"]), prev_health_dev, args.json)
        if sm.seen.get("modelV2", False):
          prev_health_mdl = print_state("modelV2", capnp_to_dict(sm["modelV2"]), prev_health_mdl, args.json)
        if sm.seen.get("controlsState", False):
          prev_health_ctrls = print_state("controlsState", capnp_to_dict(sm["controlsState"]), prev_health_ctrls, args.json)

      time.sleep(interval_s)

  except KeyboardInterrupt:
    pass


if __name__ == "__main__":
  main()