-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:10 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v3 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_4 = nil
local v_u_5 = nil
local v_u_6 = nil
local v_u_7 = nil
local v_u_8 = nil
v3:require_shared(function() --[[ Line: 10 ]]
    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_5, (ref 3): v_u_6, (ref 4): v_u_7, (ref 5): v_u_8 ]]
    v_u_4 = require(game.ReplicatedStorage.LobbyDecoration.DecorationClasses.LobbyTruckCoffee)
    v_u_5 = require(game.ReplicatedStorage.LobbyDecoration.DecorationClasses.LobbyTruckGear)
    v_u_6 = require(game.ReplicatedStorage.LobbyDecoration.DecorationClasses.LobbyTruckNews)
    v_u_7 = require(game.ReplicatedStorage.LobbyDecoration.DecorationClasses.ParkNewsStand)
    v_u_8 = require(game.ReplicatedStorage.LobbyDecoration.DecorationClasses.LobbyTruckDance)
end)
return {
    ["get_class_list"] = function(_) --[[ Name: get_class_list ]] --[[ Line: 20 ]]
        --[[ Upvalues: (copy 1): v_u_1, (ref 2): v_u_4, (ref 3): v_u_5, (ref 4): v_u_6, (ref 5): v_u_7, (ref 6): v_u_8 ]]
        return v_u_1:new({
            v_u_4,
            v_u_5,
            v_u_6,
            v_u_7,
            v_u_8
        });
    end,
    ["get_class_to_name_dict"] = function(p9) --[[ Name: get_class_to_name_dict ]] --[[ Line: 30 ]]
        --[[ Upvalues: (copy 1): v_u_2 ]]
        local v10 = v_u_2:new()
        for _, v11 in p9:get_class_list():key_itr() do
            v10:add(v11:get_decoration_name(), v11)
        end;
        return v10;
    end
};
