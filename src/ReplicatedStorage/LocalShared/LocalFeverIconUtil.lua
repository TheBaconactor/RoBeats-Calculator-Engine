-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:02 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
require(game.ReplicatedStorage.Avatar.ElementalColor)
require(game.ReplicatedStorage.Crafting.ColorTierMaterial)
require(game.ReplicatedStorage.Pets.PetDatabase)
require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
require(game.ReplicatedStorage.PlayerInfo.LeaderboardRewards)
require(game.ReplicatedStorage.PlayerInfo.BoxInfo)
require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
require(game.ReplicatedStorage.PlayerInfo.DanceRarity)
require(game.ReplicatedStorage.Shared.SPMultiDict)
require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_2 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_3 = require(game.ReplicatedStorage.SPChat.Shared.SPChatUtil)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.FeverIconInfo)
local v5 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_6 = nil
local v_u_7 = nil
local v_u_8 = nil
local v_u_9 = nil
local v_u_10 = nil
local v_u_11 = nil
v5:require_client(function() --[[ Line: 36 ]]
    --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_7, (ref 3): v_u_8, (ref 4): v_u_9, (ref 5): v_u_10, (ref 6): v_u_11 ]]
    v_u_6 = require(game.ReplicatedStorage.Lobby.Menus.ColorSelectUI)
    v_u_7 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_8 = require(game.ReplicatedStorage.Lobby.Menus.CraftingMaterialsAcquiredUI)
    v_u_9 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
    v_u_10 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_11 = require(game.ReplicatedStorage.Lobby.Menus.ValueInputUI)
end)
local v_u_22 = {
    ["set_selected_fever_icon"] = function(_, p_u_12, p13, p_u_14) --[[ Name: set_selected_fever_icon ]] --[[ Line: 47 ]]
        --[[ Upvalues: (ref 1): v_u_10, (copy 2): v_u_1 ]]
        local l__menus_0 = p_u_12._menus
        local v_u_15 = l__menus_0:push_menu(v_u_10:new(p_u_12, p_u_12._spui, l__menus_0):set_text("Saving...", "Please wait..."):set_close_button_visible(false))
        p_u_12._evt:wait_on_event_once(v_u_1.EVT_Crafting_SetFeverIconServer, function() --[[ Line: 52 ]]
            --[[ Upvalues: (copy 1): p_u_12, (copy 2): l__menus_0, (copy 3): v_u_15, (copy 4): p_u_14 ]]
            p_u_12._player_blob_manager:do_sync(function() --[[ Line: 53 ]]
                --[[ Upvalues: (ref 1): l__menus_0, (ref 2): v_u_15, (ref 3): p_u_14 ]]
                l__menus_0:remove_menu(v_u_15)
                if p_u_14 then
                    p_u_14()
                end;
            end)
        end)
        p_u_12._evt:fire_event_to_server(v_u_1.EVT_Crafting_SetFeverIconClient, p13)
    end,
    ["get_available_fevericon_id_list"] = function(_, p16) --[[ Name: get_available_fevericon_id_list ]] --[[ Line: 64 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        local v17 = v_u_4:get_playerblob_fevericon_owned_set(p16._player_blob_manager:get_player_blob(), p16._player_blob_manager:get_day_id(), p16._player_blob_manager:get_cached_collection_info()):key_list()
        v17:sort(function(p18, p19) --[[ Line: 72 ]]
            return p19 - p18;
        end)
        return v17;
    end,
    ["playerblob_get_fevericon"] = function(_, p20) --[[ Name: playerblob_get_fevericon ]] --[[ Line: 120 ]]
        return p20.FeverIcon;
    end,
    ["get_player_fevericon_assetid"] = function(_, p21) --[[ Name: get_player_fevericon_assetid ]] --[[ Line: 124 ]]
        --[[ Upvalues: (copy 1): v_u_3 ]]
        return v_u_3:playerblob_get_chat_icon((p21._player_blob_manager:get_player_blob()));
    end
}
v_u_22.show_fever_icon_list_ui = function(_, p_u_23, p_u_24) --[[ Name: show_fever_icon_list_ui ]] --[[ Line: 78 ]]
    --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_22, (copy 3): v_u_2 ]]
    local v_u_25 = p_u_23._player_blob_manager:get_player_blob()
    local v34 = p_u_23._menus:push_menu(v_u_7:new(p_u_23, p_u_23._spui, p_u_23._menus, function(p26) --[[ Line: 85 ]]
        --[[ Upvalues: (ref 1): v_u_22, (copy 2): p_u_23 ]]
        p26:set_header_text("Select icon to display...")
        for _, v27 in v_u_22:get_available_fevericon_id_list(p_u_23):key_itr() do
            p26:get_element_list():push_back(v27)
        end;
    end, function(p28, p29, p30, _, p31) --[[ Line: 91 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_22, (copy 3): v_u_25 ]]
        local v32 = v_u_2:singleton():get_fevericon_for_id(p28)
        if v32 then
            p29.Text = v32:get_name()
            if v_u_22:playerblob_get_fevericon(v_u_25) == p28 then
                p29.Text = "[Selected] " .. p29.Text
            end;
            p30.Image = v32:get_image()
            if p28 == v_u_2:singleton():get_stars_icon_id() or p28 == v_u_2:singleton():get_disabled_icon_id() then
                p31:get_description_display().Text = "Displays current mission rank as icon."
            else
                p31:get_description_display().Text = ""
            end;
        else
            p29.Text = "?"
            return;
        end;
    end, function(p33) --[[ Line: 108 ]]
        --[[ Upvalues: (ref 1): v_u_22, (copy 2): p_u_23, (copy 3): p_u_24 ]]
        if p33 ~= nil then
            v_u_22:set_selected_fever_icon(p_u_23, p33, p_u_24)
        end;
    end)):get_list_adapter()
    v34:set_do_wrap(true)
    v34:go_to_page(v34:get_page_of_element(v_u_22:playerblob_get_fevericon(v_u_25)))
end;
return v_u_22;
