-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:10 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.WebNPCAnchors)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
return {
    ["register_webnpc_anchors_on_obj"] = function(_, p_u_3, p4) --[[ Name: register_webnpc_anchors_on_obj ]] --[[ Line: 9 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
        for _, v_u_5 in pairs(p4:GetChildren()) do
            if v_u_5.Name == "NPCAnchor" then
                local v6, v7 = pcall(function() --[[ Line: 12 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_5, (copy 3): p_u_3 ]]
                    v_u_2:swap_in_random_anchor(v_u_5.PrimaryPart.CFrame, p_u_3._player_blob_manager:get_server_id())
                end)
                if not v6 then
                    v_u_1:warnf("LobbyDecorationUtil:register_webnpc_anchors_on_obj failed to swap in anchor: %s", v7)
                end;
                v_u_5.Parent = nil
            end;
        end;
    end
};
