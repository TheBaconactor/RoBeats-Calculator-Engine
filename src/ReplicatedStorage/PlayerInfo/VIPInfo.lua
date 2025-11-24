-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:06 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_3 = require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v_u_5 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.PlayerInfo.TutorialInfo)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_7 = require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_21 = {
    ["playerblob_get_vip_day"] = function(_, p9) --[[ Name: playerblob_get_vip_day ]] --[[ Line: 23 ]]
        --[[ Upvalues: (copy 1): v_u_2 ]]
        local l_VIPDay_0 = p9.VIPDay
        v_u_2:is_int(p9.VIPDay)
        return l_VIPDay_0;
    end,
    ["playerblob_set_vip_day"] = function(_, p10, p11) --[[ Name: playerblob_set_vip_day ]] --[[ Line: 29 ]]
        --[[ Upvalues: (copy 1): v_u_2 ]]
        v_u_2:is_int(p11)
        p10.VIPDay = p11
    end,
    ["get_vip_title_ids_set"] = function(_) --[[ Name: get_vip_title_ids_set ]] --[[ Line: 43 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3 ]]
        local v12 = v_u_1:new()
        for v13, v14 in v_u_3:singleton():key_itr() do
            if v14:is_vip_only() then
                v12:add(v13, true)
            end;
        end;
        return v12;
    end,
    ["is_titleid_vip_only"] = function(_, p15) --[[ Name: is_titleid_vip_only ]] --[[ Line: 61 ]]
        --[[ Upvalues: (copy 1): v_u_3 ]]
        return v_u_3:singleton():get_title_for_id(p15):is_vip_only();
    end,
    ["get_vip_fevericon_ids_set"] = function(_) --[[ Name: get_vip_fevericon_ids_set ]] --[[ Line: 66 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4 ]]
        local v16 = v_u_1:new()
        for v17, v18 in v_u_4:singleton():key_itr() do
            if v18:is_vip_only() then
                v16:add(v17, true)
            end;
        end;
        return v16;
    end,
    ["is_fevericon_id_vip_only"] = function(_, p19) --[[ Name: is_fevericon_id_vip_only ]] --[[ Line: 76 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        return v_u_4:singleton():get_fevericon_for_id(p19):is_vip_only();
    end,
    ["is_songid_vip_only"] = function(_, p20) --[[ Name: is_songid_vip_only ]] --[[ Line: 108 ]]
        --[[ Upvalues: (copy 1): v_u_5 ]]
        return v_u_5:singleton():key_is_vip(p20) == true;
    end
}
local v_u_22 = v_u_1:new():add_set_from_table_list({
    495,
    496,
    533,
    534
})
v_u_21.playerblob_get_remaining_vip_days_for_current_day = function(_, p23, p24) --[[ Name: playerblob_get_remaining_vip_days_for_current_day ]] --[[ Line: 34 ]]
    --[[ Upvalues: (copy 1): v_u_21 ]]
    return v_u_21:playerblob_get_vip_day(p23) - p24;
end;
v_u_21.playerblob_has_vip_for_current_day = function(_, p25, p26) --[[ Name: playerblob_has_vip_for_current_day ]] --[[ Line: 39 ]]
    --[[ Upvalues: (copy 1): v_u_21 ]]
    return v_u_21:playerblob_get_remaining_vip_days_for_current_day(p25, p26) >= 0;
end;
v_u_21.playerblob_set_vip_title = function(_, p27) --[[ Name: playerblob_set_vip_title ]] --[[ Line: 53 ]]
    --[[ Upvalues: (copy 1): v_u_21, (copy 2): v_u_6 ]]
    for v28, _ in v_u_21:get_vip_title_ids_set():key_itr() do
        v_u_6:set_title_id(p27, v28)
        return;
    end;
end;
v_u_21.is_songid_in_vip_songids_set = function(_, p29) --[[ Name: is_songid_in_vip_songids_set ]] --[[ Line: 81 ]]
    --[[ Upvalues: (copy 1): v_u_22, (copy 2): v_u_5, (copy 3): v_u_7 ]]
    if v_u_22:contains(p29) == false and v_u_5:singleton():key_is_remix_flagged(p29) then
        return false;
    else
        return v_u_5:singleton():key_get_audiomod(p29) ~= v_u_7.Easy;
    end;
end;
local v_u_30 = nil
v_u_21.get_vip_songids_set = function(_) --[[ Name: get_vip_songids_set ]] --[[ Line: 93 ]]
    --[[ Upvalues: (ref 1): v_u_30, (copy 2): v_u_1, (copy 3): v_u_5, (copy 4): v_u_21 ]]
    if v_u_30 == nil then
        local v31 = v_u_1:new()
        local v32 = v_u_5:singleton():all_keys()
        for v33 = 1, v32:count() do
            local v34 = v32:get(v33)
            if v_u_21:is_songid_in_vip_songids_set(v34) then
                v31:add(v34, true)
            end;
        end;
        v_u_30 = v31
    end;
    return v_u_30;
end;
v_u_21.playerblob_has_access_to_song = function(_, p35, p36, p37, p38) --[[ Name: playerblob_has_access_to_song ]] --[[ Line: 112 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_7, (copy 3): v_u_21, (copy 4): v_u_6, (copy 5): v_u_8 ]]
    return v_u_5:singleton():key_get_audiomod(p36) == v_u_7.Easy and true or (v_u_21:playerblob_has_vip_for_current_day(p35, p37) and v_u_21:get_vip_songids_set():contains(p36) and true or (v_u_6:get_song_key_owned_count(p35, p36) > 0 and true or (v_u_8:get_playerblob_songkey_in_collection(p35, p36, p38) == true and true or false)));
end;
return v_u_21;
