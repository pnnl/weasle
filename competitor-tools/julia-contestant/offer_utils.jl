using JSON
using Dates

struct NpEncoder <: JSON.Encoder
    function NpEncoder()
        new()
    end
end

function JSON.encode(encoder::NpEncoder, obj)
    if isa(obj, Integer)
        return Int(obj)
    elseif isa(obj, Float64)
        return Float64(obj)
    elseif isa(obj, Array)
        return JSON.encode(encoder, collect(obj))
    end
    return JSON.encode(encoder, obj)
end

function load_json(filename, filedir="./")
    json_dict = JSON.parsefile(joinpath(filedir, "$filename.json"))
    return json_dict
end

function split_mktid(mktid)
    split_idx = findfirst(isequal('2'), mktid)
    mkt_type = mktid[1:split_idx-1]
    start_time = mktid[split_idx:end]
    return mkt_type, start_time
end

function get_latest_forecast()
    forecast = JSON.parsefile("../forecast.json")
    demand = forecast["demand"]
    wind = forecast["wind"]
    solar = forecast["solar"]
    renewables = wind + solar
    return demand, renewables
end

function compute_offers(resources, times, demand, renewables)
    offer_keys = ["cost_rgu", "cost_rgd", "cost_spr", "cost_nsp", "block_ch_mc", "block_dc_mc",
                  "block_soc_mc", "block_ch_mq", "block_dc_mq", "block_soc_mq", "soc_end",
                  "bid_soc", "init_en", "init_status", "ramp_up", "ramp_dn", "socmax", "socmin",
                  "soc_begin", "eff_ch", "eff_dc", "chmax", "dcmax"]
    offer_vals = [3, 3, 0, 0, [22, 19.5], [27.6, 35], [36, 20], [20, 16], [20, 16], [80, 56.8], 28.8,
                  false, 0, 0, 9999, 9999, 136.8, 28.8, 136.8, 0.9, 1, 36, 36]
    use_time = [true, true, true, true, true, true, true, true, true, true, false, false, false,
                false, false, false, false, false, false, false, false, true, true]
    offer_out = Dict()
    for rid in resources
        resource_offer = Dict()
        for (i, key) in enumerate(offer_keys)
            if use_time[i]
                time_dict = Dict()
                for t in times
                    time_dict[t] = offer_vals[i]
                end
            else
                time_dict = offer_vals[i]
            end
            resource_offer[key] = time_dict
        end
        offer_out[rid] = resource_offer
    end
    return offer_out
end

function save_offer(offer, time_step)
    if time_step != 4
        json_file = "offer_$time_step.json"
        JSON.print(json_file, offer, indent=4, jsonobject=NpEncoder())
    end
end


