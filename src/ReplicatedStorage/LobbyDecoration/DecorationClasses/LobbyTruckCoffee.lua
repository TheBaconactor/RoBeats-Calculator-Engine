-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:10 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.Override)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.WebNPCAnchors)
local v_u_2 = require(game.ReplicatedStorage.LobbyDecoration.DecorationClasses.LobbyDecorationBase)
local v_u_3 = require(game.ReplicatedStorage.LobbyDecoration.LobbyDecorationUtil)
return {
    ["get_decoration_name"] = function(_) --[[ Name: get_decoration_name ]] --[[ Line: 10 ]]
        return "LobbyTruckCoffee";
    end,
    ["new"] = function(_, p_u_4) --[[ Name: new ]] --[[ Line: 12 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_3 ]]
        local v5 = v_u_2:new()
        v_u_1:get_base_fn(v5, "on_client_startup")
        v5.on_client_startup = function(_, p6) --[[ Name: on_client_startup ]] --[[ Line: 16 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_4 ]]
            v_u_3:register_webnpc_anchors_on_obj(p6, p_u_4)
        end;
        return v5;
    end
};
