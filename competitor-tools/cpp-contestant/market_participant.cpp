#include "json.hpp"
#include <iostream>
#include <vector>
#include <sstream>
#include <fstream>

using namespace std;
using json = nlohmann::json;

void save_offer(json offer, string time_step)
{
   ostringstream oss;
   oss << "offer_" << time_step << ".json";
   string filename = oss.str();
   fstream file;
   file.open(filename, ios::out);
   file << offer;
}

json compute_offer(string rid, float soc, vector<string> times)
{
  // Write out the lists from offer_utils.py
  vector<string> offer_keys = {"cost_rgu", "cost_rgd", "cost_spr", "cost_nsp", "block_ch_mc", "block_dc_mc", 
                  "block_soc_mc", "block_ch_mq", "block_dc_mq", "block_soc_mq", "soc_end", 
                  "bid_soc", "init_en", "init_status", "ramp_up", "ramp_dn", "socmax", "socmin",
                  "soc_begin", "eff_ch", "eff_dc", "chmax", "dcmax"};
  vector<float> offer_vals = {3, 3, 0, 0, 20, 22, 0, 125, 125, 608, 128, 0, 0, 0, 9999, 9999,
				608, 128, soc, 0.9, 1, 125, 125};
  vector<bool> use_time = {true, true, true, true, true, true, true, true, true, true, false, false, false,
                false, false, false, false, false, false, false, false, true, true};
  
  // make a json dictionary
  json offer_out;
  json resource_offer;
  for (int i=0; i < offer_keys.size(); i++){
      if (use_time[i]){
        json time_dict;
        for (string const& t : times)
           time_dict[t] = offer_vals[i];
        resource_offer[offer_keys[i]] = time_dict;
      }
      else {
        if (offer_keys[i] == "bid_soc")
           resource_offer[offer_keys[i]] = false;
        else
           resource_offer[offer_keys[i]] = offer_vals[i];
      }
  }
  offer_out[rid] = resource_offer;
  return offer_out;
}

int main(int argc, char** argv)
{
  string time_step = argv[1];
  json market{json::parse(argv[2])};
  json resource{json::parse(argv[3])};
  vector<string> times;
  for (auto it = market["timestamps"].begin(); it != market["timestamps"].end(); it++){
      times.push_back(*it);
  }

  string rid;
  for (auto rs : resource["status"].items()){
    rid = rs.key();
    break;
  }
  float soc = resource["status"][rid]["soc"];
  json offer_out = compute_offer(rid, soc, times);
  save_offer(offer_out, time_step);
}
