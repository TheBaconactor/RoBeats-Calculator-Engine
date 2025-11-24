-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:03 PM
-- Cached decompilation

local v1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
local v3 = {}
local v_u_4 = nil
local v_u_5 = v1:new()
local l_Folder_0 = Instance.new("Folder", game.ReplicatedStorage)
l_Folder_0.Name = "LocalCharacterCloneCache"
v3.set_local_services = function(_, p6) --[[ Name: set_local_services ]] --[[ Line: 12 ]]
    --[[ Upvalues: (ref 1): v_u_4 ]]
    v_u_4 = p6
end;
local function _() --[[ Name: get_id_to_playerinfo ]] --[[ Line: 16 ]]
    --[[ Upvalues: (ref 1): v_u_4 ]]
    return v_u_4._lobby_join:get_character_manager():get_id_to_playerinfo();
end;
v3.playerid_disconnecting = function(_, p7) --[[ Name: playerid_disconnecting ]] --[[ Line: 18 ]]
    --[[ Upvalues: (copy 1): v_u_5 ]]
    if v_u_5:contains(p7) then
        local v8 = v_u_5:get(p7)
        v_u_5:remove(p7)
        v8:Destroy()
    end;
end;
v3.get_cached_match_preview_npc_for_userid = function(_, p9) --[[ Name: get_cached_match_preview_npc_for_userid ]] --[[ Line: 26 ]]
    --[[ Upvalues: (copy 1): v_u_5 ]]
    local v10 = v_u_5:get(p9)
    v_u_5:remove(p9)
    return v10;
end;
v3.cache_match_preview_npc_for_userid = function(_, p11, p12) --[[ Name: cache_match_preview_npc_for_userid ]] --[[ Line: 32 ]]
    --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_2, (copy 3): v_u_5, (copy 4): l_Folder_0 ]]
    if v_u_4._lobby_join:get_character_manager():get_id_to_playerinfo():contains(p11) == false then
        p12:Destroy()
        return v_u_2:warnf("CharacterCloneCache:cache_match_preview_npc_for_userid player_userid(%s) not found", (tostring(p11)));
    end;
    v_u_5:add(p11, p12)
    p12.Parent = l_Folder_0
end;
v3.get_cached_count = function(_) --[[ Name: get_cached_count ]] --[[ Line: 41 ]]
    --[[ Upvalues: (copy 1): v_u_5 ]]
    return v_u_5:count();
end;
return v3;
