-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:13 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.EditorGame.Data.EditorGameData)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_4 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.ForwardCompatSerialization)
local v_u_6 = {
    ["CustomMapData"] = require(game.ReplicatedStorage.EditorGame.Data.CustomMapData),
    ["SavedMapInfo"] = require(game.ReplicatedStorage.EditorGame.Data.SavedMapInfo),
    ["CreatorData"] = require(game.ReplicatedStorage.EditorGame.Data.CreatorData)
}
v_u_6.validate_saved_map_info = function(_, p7) --[[ Name: validate_saved_map_info ]] --[[ Line: 21 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_6 ]]
    if v_u_4:singleton():contains_key(p7:get_source_songkey()) == true then
        if v_u_4:singleton():key_get_audiomod(p7:get_source_songkey()) == v_u_4.MOD_NORMAL then
            if v_u_4:singleton():get_songkey_priority(p7:get_source_songkey()) == v_u_4.SongPriority.Hidden then
                return false, string.format("Invalid source songkey(%s) priority(%d)", p7:get_source_songkey(), v_u_4:singleton():get_songkey_priority(p7:get_source_songkey()));
            elseif v_u_4:singleton():key_is_remix_flagged(p7:get_source_songkey()) == true then
                return false, string.format("Invalid source songkey(%s) flagged as hidden", p7:get_source_songkey());
            elseif #p7:get_custom_map_name() > v_u_6.SavedMapInfo:get_map_name_max_length() then
                return false, string.format("Map name too long(%d) max(%d)", #p7:get_custom_map_name(), v_u_6.SavedMapInfo:get_map_name_max_length());
            else
                return true, "";
            end;
        else
            return false, string.format("Invalid source songkey(%s) audiomod(%d)", p7:get_source_songkey(), v_u_4:singleton():key_get_audiomod(p7:get_source_songkey()));
        end;
    else
        return false, string.format("Invalid source songkey(%s)", p7:get_source_songkey());
    end;
end;
v_u_6.saved_map_info_custom_map_data_passes_validation = function(_, p8, p9) --[[ Name: saved_map_info_custom_map_data_passes_validation ]] --[[ Line: 42 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_1 ]]
    local v10, v11 = v_u_6:validate_saved_map_info(p8)
    if v10 == true then
        if p9:get_notes():count() > v_u_6.CustomMapData:get_max_note_count() then
            return false, string.format("Too many notes(%d) max(%d)", p9:get_notes():count(), v_u_6.CustomMapData:get_max_note_count());
        elseif p9:get_timing_points():count() > v_u_6.CustomMapData:get_max_timing_point_count() then
            return false, string.format("Too many timing points(%d) max(%d)", p9:get_timing_points():count(), v_u_6.CustomMapData:get_max_timing_point_count());
        else
            local v12, v13 = v_u_1:validate_note_data_list(p9:get_notes(), p8:get_source_songkey())
            if v12 == true then
                return true, "";
            else
                return false, string.format("Note data failed validation: %s", v13);
            end;
        end;
    else
        return false, string.format(v11);
    end;
end;
v_u_6.validate_custom_map_key_components = function(_, p14) --[[ Name: validate_custom_map_key_components ]] --[[ Line: 64 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_4, (copy 3): v_u_6 ]]
    local v15 = v_u_2:new(string.split(p14, "@"))
    if v15:count() == 3 then
        local v16 = v15:get(1)
        local v17 = tonumber(v15:get(2))
        local v18 = tonumber(v15:get(3))
        if typeof(v16) == "string" and (typeof(v17) == "number" and typeof(v18) == "number") then
            if v_u_4:singleton():contains_key(v17) == true then
                if v18 < 0 or v_u_6.SavedMapInfo:get_max_recent_saved_map_info_count() * 2 < v18 then
                    return false;
                elseif math.floor(v18) == v18 then
                    return true, v16, v17, v18;
                else
                    return false;
                end;
            else
                return false;
            end;
        else
            return false;
        end;
    else
        return false;
    end;
end;
local v_u_19 = {
    ["Global"] = 1,
    ["SongKey"] = 2,
    ["ArtistEvent"] = 3,
    ["MyLikedMaps"] = 4
}
local v_u_20 = v_u_2:new()
for _, v21 in v_u_5:new(v_u_19):key_itr() do
    v_u_20:push_back(v21)
end;
v_u_19.all_publish_categories_list = function(_) --[[ Name: all_publish_categories_list ]] --[[ Line: 104 ]]
    --[[ Upvalues: (copy 1): v_u_20 ]]
    return v_u_20;
end;
v_u_6.PublishCategory = v_u_19
local v_u_22 = {}
v_u_6.CheckPublishInfo = v_u_22
v_u_22.new = function(_) --[[ Name: new ]] --[[ Line: 109 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_19, (copy 3): v_u_3 ]]
    local v23 = {}
    local v_u_24 = 0
    local v_u_25 = v_u_5:new({
        [v_u_19.Global] = false,
        [v_u_19.SongKey] = false,
        [v_u_19.ArtistEvent] = false
    })
    local v_u_26 = v_u_5:new({
        [v_u_19.Global] = 0,
        [v_u_19.SongKey] = 0,
        [v_u_19.ArtistEvent] = 0
    })
    v23.get_publish_cost_star_currency = function(_) --[[ Name: get_publish_cost_star_currency ]] --[[ Line: 126 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return v_u_24;
    end;
    v23.set_publish_cost_star_currency = function(_, p27) --[[ Name: set_publish_cost_star_currency ]] --[[ Line: 127 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_24 ]]
        v_u_3:is_int(p27)
        v_u_24 = p27
    end;
    v23.get_publish_category_is_published = function(_, p28) --[[ Name: get_publish_category_is_published ]] --[[ Line: 129 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_19, (copy 3): v_u_25 ]]
        v_u_3:is_enum_member(p28, v_u_19)
        return v_u_25:get(p28);
    end;
    v23.set_publish_category_is_published = function(_, p29, p30) --[[ Name: set_publish_category_is_published ]] --[[ Line: 133 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_19, (copy 3): v_u_25 ]]
        v_u_3:is_enum_member(p29, v_u_19)
        v_u_3:is_bool(p30)
        v_u_25:add(p29, p30)
    end;
    v23.get_publish_category_published_count = function(_, p31) --[[ Name: get_publish_category_published_count ]] --[[ Line: 138 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_19, (copy 3): v_u_26 ]]
        v_u_3:is_enum_member(p31, v_u_19)
        return v_u_26:get(p31);
    end;
    v23.set_publish_category_published_count = function(_, p32, p33) --[[ Name: set_publish_category_published_count ]] --[[ Line: 142 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_19, (copy 3): v_u_26 ]]
        v_u_3:is_enum_member(p32, v_u_19)
        v_u_3:is_int(p33)
        v_u_26:add(p32, p33)
    end;
    v23.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 149 ]]
        --[[ Upvalues: (copy 1): v_u_25, (copy 2): v_u_26, (ref 3): v_u_24 ]]
        local v34 = {}
        for v35, v36 in v_u_25:key_itr() do
            v34[tostring(v35)] = v36
        end;
        local v37 = {}
        for v38, v39 in v_u_26:key_itr() do
            v37[tostring(v38)] = v39
        end;
        return {
            ["PublishCostStarCurrency"] = v_u_24,
            ["PublishCategoryIsPublishedList"] = v34,
            ["PublishCategoryPublishedCountList"] = v37
        };
    end;
    return v23;
end;
v_u_22.from_table = function(_, p40) --[[ Name: from_table ]] --[[ Line: 168 ]]
    --[[ Upvalues: (copy 1): v_u_22, (copy 2): v_u_3, (copy 3): v_u_19 ]]
    local v41 = v_u_22:new()
    v41:set_publish_cost_star_currency(p40.PublishCostStarCurrency)
    for v42, v43 in pairs(p40.PublishCategoryIsPublishedList) do
        local v44 = tonumber(v42)
        if p40.PublishCategoryPublishedCountList[v42] ~= nil and v_u_3:test_enum_member(v44, v_u_19) then
            v41:set_publish_category_is_published(v44, v43)
            v41:set_publish_category_published_count(v44, p40.PublishCategoryPublishedCountList[v42])
        end;
    end;
    return v41;
end;
local v_u_45 = {}
v_u_6.LoadCustomMapAdditionalInfo = v_u_45
v_u_45.new = function(_) --[[ Name: new ]] --[[ Line: 184 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    local v46 = {}
    local v_u_47 = false
    v46.has_player_already_liked = function(_) --[[ Name: has_player_already_liked ]] --[[ Line: 188 ]]
        --[[ Upvalues: (ref 1): v_u_47 ]]
        return v_u_47;
    end;
    v46.set_player_already_liked = function(_, p48) --[[ Name: set_player_already_liked ]] --[[ Line: 189 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_47 ]]
        v_u_3:is_bool(p48)
        v_u_47 = p48
    end;
    v46.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 194 ]]
        --[[ Upvalues: (ref 1): v_u_47 ]]
        return {
            ["HasPlayerAlreadyLiked"] = v_u_47
        };
    end;
    return v46;
end;
v_u_45.from_table = function(_, p49) --[[ Name: from_table ]] --[[ Line: 202 ]]
    --[[ Upvalues: (copy 1): v_u_45 ]]
    local v50 = v_u_45:new()
    v50:set_player_already_liked(p49.HasPlayerAlreadyLiked)
    return v50;
end;
return v_u_6;
