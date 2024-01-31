using Pkg
Pkg.activate(DEPOT_PATH[1])
using JSON
using ArgParse
using LinearAlgebra

mutable struct MakeOffer
    times::Array{String}
    resources::Array{String}
end

function make_me_an_offer(self::MakeOffer, time_step::Int, forecast::Dict{String, Any})
    self.demand = forecast["demand"]
    self.renewables = convert(Array{Float64}, forecast["wind"]) + convert(Array{Float64}, forecast["solar"])
    self.renewables = convert(Array{Any}, self.renewables)

    self.offer = compute_offers(self.resources, self.times, self.demand, self.renewables)
    save_offer(self.offer, time_step)
end

function main()
    parser = ArgParse.ArgumentParser()
    ArgParse.add_argument(parser, "time_step", type=Int, help="Integer time step tracking the progress of the simulated market.")
    ArgParse.add_argument(parser, "market_info", help="json formatted dictionary with market information.")
    ArgParse.add_argument(parser, "resource_info", help="json formatted dictionary with resource information.")
    args = ArgParse.parse_args(parser)

    mi = JSON.parse(args.market_info)
    ri = JSON.parse(args.resource_info)
    times = [k for k in keys(mi["intervals"])]
    forecast = mi["forecast"]
    resources = [r for r in keys(ri["status"])]
    myoffer = MakeOffer(times, resources)
    make_me_an_offer(myoffer, args.time_step, forecast)
end

main()


