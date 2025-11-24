-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:13 PM
-- Cached decompilation

require(game.ReplicatedStorage.EditorGame.Data.EditorGameData)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.ForwardCompatSerialization)
local v_u_11 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 13 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
        local v3 = {}
        local v_u_4 = ""
        v3.get_creator_name = function(_) --[[ Name: get_creator_name ]] --[[ Line: 17 ]]
            --[[ Upvalues: (ref 1): v_u_4 ]]
            return v_u_4;
        end;
        v3.set_creator_name = function(_, p5) --[[ Name: set_creator_name ]] --[[ Line: 18 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_4 ]]
            v_u_1:is_string(p5)
            v_u_4 = p5
        end;
        local v_u_6 = 0
        v3.get_creator_rbxid = function(_) --[[ Name: get_creator_rbxid ]] --[[ Line: 24 ]]
            --[[ Upvalues: (ref 1): v_u_6 ]]
            return v_u_6;
        end;
        v3.set_creator_rbxid = function(_, p7) --[[ Name: set_creator_rbxid ]] --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_6 ]]
            v_u_1:is_int(p7)
            v_u_6 = p7
        end;
        local v_u_8 = 0
        v3.get_received_like_count = function(_) --[[ Name: get_received_like_count ]] --[[ Line: 31 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            return v_u_8;
        end;
        v3.set_received_like_count = function(_, p9) --[[ Name: set_received_like_count ]] --[[ Line: 32 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_8 ]]
            v_u_1:is_int(p9)
            v_u_8 = p9
        end;
        local v_u_10 = v_u_2:new()
        v3.get_forward_compat_serialization = function(_) --[[ Name: get_forward_compat_serialization ]] --[[ Line: 38 ]]
            --[[ Upvalues: (copy 1): v_u_10 ]]
            return v_u_10;
        end;
        v3.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 40 ]]
            --[[ Upvalues: (copy 1): v_u_10, (ref 2): v_u_4, (ref 3): v_u_6, (ref 4): v_u_8 ]]
            return v_u_10:write_forward_compat_properties_to_table({
                ["CreatorName"] = v_u_4,
                ["CreatorRbxID"] = v_u_6,
                ["ReceivedLikeCount"] = v_u_8
            });
        end;
        return v3;
    end
}
v_u_11.from_table = function(_, p12) --[[ Name: from_table ]] --[[ Line: 51 ]]
    --[[ Upvalues: (copy 1): v_u_11 ]]
    local v13 = v_u_11:new()
    v13:set_creator_name(p12.CreatorName)
    v13:set_creator_rbxid(p12.CreatorRbxID)
    if p12.ReceivedLikeCount ~= nil then
        v13:set_received_like_count(p12.ReceivedLikeCount)
    end;
    return v13;
end;
v_u_11.from_datastore_forward_compat_table = function(_, p14) --[[ Name: from_datastore_forward_compat_table ]] --[[ Line: 61 ]]
    --[[ Upvalues: (copy 1): v_u_11 ]]
    local v15 = v_u_11:from_table(p14)
    v15:get_forward_compat_serialization():store_forward_compat_properties(v15:to_table(), p14)
    return v15;
end;
return v_u_11;
