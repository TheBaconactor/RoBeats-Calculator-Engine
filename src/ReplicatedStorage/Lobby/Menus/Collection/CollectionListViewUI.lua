-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:49 PM
-- Time elapsed: 28 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_7 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_8 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_9 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.DanceRarity)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.DanceType)
local v_u_14 = require(game.ReplicatedStorage.Avatar.SPAvatarUtil)
local v_u_15 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_16 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_17 = require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_18 = require(game.ReplicatedStorage.Pets.PetInfoBase)
local v_u_19 = require(game.ReplicatedStorage.GameStage.GameStageDatabase)
local v_u_20 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v_u_21 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_22 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v_u_23 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_24 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_25 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_26 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_27 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v28 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_29 = nil
local v_u_30 = nil
local v_u_31 = nil
local v_u_32 = nil
local v_u_33 = nil
local v_u_34 = nil
local v_u_35 = nil
local v_u_36 = nil
local v_u_37 = nil
local v_u_38 = nil
local v_u_39 = nil
local v_u_40 = nil
v28:require_client(function() --[[ Line: 49 ]]
    --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_30, (ref 3): v_u_31, (ref 4): v_u_32, (ref 5): v_u_33, (ref 6): v_u_34, (ref 7): v_u_35, (ref 8): v_u_36, (ref 9): v_u_37, (ref 10): v_u_38, (ref 11): v_u_39, (ref 12): v_u_40 ]]
    v_u_29 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_30 = require(game.ReplicatedStorage.Lobby.Menus.PreviewCharacterUI)
    v_u_31 = require(game.ReplicatedStorage.Lobby.Menus.PreviewImageUI)
    v_u_32 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
    v_u_33 = require(game.ReplicatedStorage.LocalShared.LocalFeverIconUtil)
    v_u_34 = require(game.ReplicatedStorage.Lobby.UI.MatchMakingV3GameStageSelectSection)
    v_u_35 = require(game.ReplicatedStorage.Lobby.Menus.TextInputUI)
    v_u_36 = require(game.ReplicatedStorage.Lobby.Menus.GearSelectUI)
    v_u_37 = require(game.ReplicatedStorage.Lobby.Menus.CraftingMaterialsAcquiredUI)
    v_u_38 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
    v_u_39 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
    v_u_40 = require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
end)
local v41 = {}
local v_u_42 = 1
local v_u_43 = nil
v41.show_collection_ui = function(_, p_u_44, p_u_45, p_u_46) --[[ Name: show_collection_ui ]] --[[ Line: 73 ]]
    --[[ Upvalues: (copy 1): v_u_10, (ref 2): v_u_29, (ref 3): v_u_43, (copy 4): v_u_5, (copy 5): v_u_6, (ref 6): v_u_30, (copy 7): v_u_11, (copy 8): v_u_13, (copy 9): v_u_1, (copy 10): v_u_12, (copy 11): v_u_22, (copy 12): v_u_14, (copy 13): v_u_27, (copy 14): v_u_15, (copy 15): v_u_16, (copy 16): v_u_25, (copy 17): v_u_24, (ref 18): v_u_36, (copy 19): v_u_17, (copy 20): v_u_18, (ref 21): v_u_31, (copy 22): v_u_19, (ref 23): v_u_34, (copy 24): v_u_26, (copy 25): v_u_20, (ref 26): v_u_33, (ref 27): v_u_40, (copy 28): v_u_21, (copy 29): v_u_8, (copy 30): v_u_9, (ref 31): v_u_42, (copy 32): v_u_2, (copy 33): v_u_3, (copy 34): v_u_4, (ref 35): v_u_35, (copy 36): v_u_23, (ref 37): v_u_38, (ref 38): v_u_39, (ref 39): v_u_37, (copy 40): v_u_7 ]]
    local function f_get_collection_info() --[[ Name: get_collection_info ]] --[[ Line: 74 ]]
        --[[ Upvalues: (copy 1): p_u_44 ]]
        return p_u_44._player_blob_manager:get_cached_collection_info();
    end;
    local function _(p47) --[[ Name: is_collection_entry ]] --[[ Line: 75 ]]
        local v48
        if typeof(p47) == "table" then
            v48 = p47.get_collection_id ~= nil
        else
            v48 = false
        end;
        return v48;
    end;
    local function f_get_collection_type_owned_of_total_string(p49) --[[ Name: get_collection_type_owned_of_total_string ]] --[[ Line: 76 ]]
        --[[ Upvalues: (copy 1): p_u_44, (ref 2): v_u_10 ]]
        return string.format("%d / %d", p_u_44._player_blob_manager:get_cached_collection_info():get_collection_type_owned_count(p49), v_u_10:get_collection_type_display_entry_count(p49));
    end;
    local function f_confirm_register_will_remove_items(p50, p51, p_u_52) --[[ Name: confirm_register_will_remove_items ]] --[[ Line: 84 ]]
        --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_46, (ref 3): v_u_29, (copy 4): p_u_44, (copy 5): p_u_45 ]]
        local v53
        if p51 == 1 then
            v53 = string.format("this %s", v_u_10:type_to_name(p50, 1))
        else
            v53 = string.format("these %d %s", p51, v_u_10:type_to_name(p50, p51))
        end;
        p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Confirm", string.format("Are you sure you want to register %s? These items will be removed from your inventory, but you will still be able to access them elsewhere.", v53)):set_okay_button_fn(function() --[[ Line: 101 ]]
            --[[ Upvalues: (copy 1): p_u_52 ]]
            p_u_52()
        end))
    end;
    local function _() --[[ Name: create_loading_menu ]] --[[ Line: 107 ]]
        --[[ Upvalues: (copy 1): p_u_46, (ref 2): v_u_29, (copy 3): p_u_44, (copy 4): p_u_45 ]]
        return p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Loading...", "Please wait..."):set_close_button_visible(false));
    end;
    local function _(p_u_54, p_u_55, p_u_56) --[[ Name: on_register_collection_type_registered_count ]] --[[ Line: 115 ]]
        --[[ Upvalues: (copy 1): p_u_44, (ref 2): v_u_43, (copy 3): p_u_46, (ref 4): v_u_29, (copy 5): p_u_45, (ref 6): v_u_10, (ref 7): v_u_5 ]]
        p_u_44._player_blob_manager:do_sync(function() --[[ Line: 116 ]]
            --[[ Upvalues: (ref 1): p_u_44, (copy 2): p_u_54, (ref 3): v_u_43, (ref 4): p_u_46, (ref 5): v_u_29, (ref 6): p_u_45, (copy 7): p_u_56, (ref 8): v_u_10, (copy 9): p_u_55, (ref 10): v_u_5 ]]
            p_u_44._menus:remove_menu(p_u_54)
            v_u_43 = nil
            p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Registered!", string.format("Registered %d new %s to your collection.", p_u_56, v_u_10:type_to_name(p_u_55, p_u_56))))
            p_u_44._sfx_manager:play_sfx(v_u_5.SFX_ACQUIRE)
        end)
    end;
    local function f_register_collection_type_unregistered(p_u_57) --[[ Name: register_collection_type_unregistered ]] --[[ Line: 127 ]]
        --[[ Upvalues: (copy 1): p_u_46, (ref 2): v_u_29, (copy 3): p_u_44, (copy 4): p_u_45, (ref 5): v_u_6, (ref 6): v_u_43, (ref 7): v_u_10, (ref 8): v_u_5, (copy 9): f_get_collection_info, (copy 10): f_confirm_register_will_remove_items ]]
        local function _() --[[ Name: do_register ]] --[[ Line: 128 ]]
            --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_29, (ref 3): p_u_44, (ref 4): p_u_45, (ref 5): v_u_6, (copy 6): p_u_57, (ref 7): v_u_43, (ref 8): v_u_10, (ref 9): v_u_5 ]]
            local v_u_58 = p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_44._evt:wait_on_event_once(v_u_6.EVT_Collection_RegisterAllOfCollectionType_Server, function(p_u_59) --[[ Line: 130 ]]
                --[[ Upvalues: (copy 1): v_u_58, (ref 2): p_u_57, (ref 3): p_u_44, (ref 4): v_u_43, (ref 5): p_u_46, (ref 6): v_u_29, (ref 7): p_u_45, (ref 8): v_u_10, (ref 9): v_u_5 ]]
                local v_u_60 = v_u_58
                local v_u_61 = p_u_57
                p_u_44._player_blob_manager:do_sync(function() --[[ Line: 116 ]]
                    --[[ Upvalues: (ref 1): p_u_44, (copy 2): v_u_60, (ref 3): v_u_43, (ref 4): p_u_46, (ref 5): v_u_29, (ref 6): p_u_45, (copy 7): p_u_59, (ref 8): v_u_10, (copy 9): v_u_61, (ref 10): v_u_5 ]]
                    p_u_44._menus:remove_menu(v_u_60)
                    v_u_43 = nil
                    p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Registered!", string.format("Registered %d new %s to your collection.", p_u_59, v_u_10:type_to_name(v_u_61, p_u_59))))
                    p_u_44._sfx_manager:play_sfx(v_u_5.SFX_ACQUIRE)
                end)
            end)
            p_u_44._evt:fire_event_to_server(v_u_6.EVT_Collection_RegisterAllOfCollectionType_Client, p_u_57)
        end;
        if v_u_10:does_collection_type_require_playerblob_update(p_u_57) then
            f_confirm_register_will_remove_items(p_u_57, v_u_10:get_playerblob_collection_type_collection_info_unregistered_owned_entries_list(p_u_44._player_blob_manager:get_player_blob(), p_u_57, f_get_collection_info()):count(), function() --[[ Line: 138 ]]
                --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_29, (ref 3): p_u_44, (ref 4): p_u_45, (ref 5): v_u_6, (copy 6): p_u_57, (ref 7): v_u_43, (ref 8): v_u_10, (ref 9): v_u_5 ]]
                local v_u_62 = p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                p_u_44._evt:wait_on_event_once(v_u_6.EVT_Collection_RegisterAllOfCollectionType_Server, function(p_u_63) --[[ Line: 130 ]]
                    --[[ Upvalues: (copy 1): v_u_62, (ref 2): p_u_57, (ref 3): p_u_44, (ref 4): v_u_43, (ref 5): p_u_46, (ref 6): v_u_29, (ref 7): p_u_45, (ref 8): v_u_10, (ref 9): v_u_5 ]]
                    local v_u_64 = v_u_62
                    local v_u_65 = p_u_57
                    p_u_44._player_blob_manager:do_sync(function() --[[ Line: 116 ]]
                        --[[ Upvalues: (ref 1): p_u_44, (copy 2): v_u_64, (ref 3): v_u_43, (ref 4): p_u_46, (ref 5): v_u_29, (ref 6): p_u_45, (copy 7): p_u_63, (ref 8): v_u_10, (copy 9): v_u_65, (ref 10): v_u_5 ]]
                        p_u_44._menus:remove_menu(v_u_64)
                        v_u_43 = nil
                        p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Registered!", string.format("Registered %d new %s to your collection.", p_u_63, v_u_10:type_to_name(v_u_65, p_u_63))))
                        p_u_44._sfx_manager:play_sfx(v_u_5.SFX_ACQUIRE)
                    end)
                end)
                p_u_44._evt:fire_event_to_server(v_u_6.EVT_Collection_RegisterAllOfCollectionType_Client, p_u_57)
            end)
        else
            local v_u_66 = p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_44._evt:wait_on_event_once(v_u_6.EVT_Collection_RegisterAllOfCollectionType_Server, function(p_u_67) --[[ Line: 130 ]]
                --[[ Upvalues: (copy 1): v_u_66, (copy 2): p_u_57, (ref 3): p_u_44, (ref 4): v_u_43, (ref 5): p_u_46, (ref 6): v_u_29, (ref 7): p_u_45, (ref 8): v_u_10, (ref 9): v_u_5 ]]
                local v_u_68 = v_u_66
                local v_u_69 = p_u_57
                p_u_44._player_blob_manager:do_sync(function() --[[ Line: 116 ]]
                    --[[ Upvalues: (ref 1): p_u_44, (copy 2): v_u_68, (ref 3): v_u_43, (ref 4): p_u_46, (ref 5): v_u_29, (ref 6): p_u_45, (copy 7): p_u_67, (ref 8): v_u_10, (copy 9): v_u_69, (ref 10): v_u_5 ]]
                    p_u_44._menus:remove_menu(v_u_68)
                    v_u_43 = nil
                    p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Registered!", string.format("Registered %d new %s to your collection.", p_u_67, v_u_10:type_to_name(v_u_69, p_u_67))))
                    p_u_44._sfx_manager:play_sfx(v_u_5.SFX_ACQUIRE)
                end)
            end)
            p_u_44._evt:fire_event_to_server(v_u_6.EVT_Collection_RegisterAllOfCollectionType_Client, p_u_57)
        end;
    end;
    local function f_register_collection_type_collection_id(p_u_70, p_u_71) --[[ Name: register_collection_type_collection_id ]] --[[ Line: 146 ]]
        --[[ Upvalues: (copy 1): p_u_46, (ref 2): v_u_29, (copy 3): p_u_44, (copy 4): p_u_45, (ref 5): v_u_6, (ref 6): v_u_43, (ref 7): v_u_10, (ref 8): v_u_5, (copy 9): f_confirm_register_will_remove_items ]]
        local function _() --[[ Name: do_register ]] --[[ Line: 147 ]]
            --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_29, (ref 3): p_u_44, (ref 4): p_u_45, (ref 5): v_u_6, (copy 6): p_u_70, (ref 7): v_u_43, (ref 8): v_u_10, (ref 9): v_u_5, (copy 10): p_u_71 ]]
            local v_u_72 = p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_44._evt:wait_on_event_once(v_u_6.EVT_Collection_RegisterCollectionTypeAndID_Server, function(p_u_73) --[[ Line: 149 ]]
                --[[ Upvalues: (copy 1): v_u_72, (ref 2): p_u_70, (ref 3): p_u_44, (ref 4): v_u_43, (ref 5): p_u_46, (ref 6): v_u_29, (ref 7): p_u_45, (ref 8): v_u_10, (ref 9): v_u_5 ]]
                local v_u_74 = v_u_72
                local v_u_75 = p_u_70
                p_u_44._player_blob_manager:do_sync(function() --[[ Line: 116 ]]
                    --[[ Upvalues: (ref 1): p_u_44, (copy 2): v_u_74, (ref 3): v_u_43, (ref 4): p_u_46, (ref 5): v_u_29, (ref 6): p_u_45, (copy 7): p_u_73, (ref 8): v_u_10, (copy 9): v_u_75, (ref 10): v_u_5 ]]
                    p_u_44._menus:remove_menu(v_u_74)
                    v_u_43 = nil
                    p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Registered!", string.format("Registered %d new %s to your collection.", p_u_73, v_u_10:type_to_name(v_u_75, p_u_73))))
                    p_u_44._sfx_manager:play_sfx(v_u_5.SFX_ACQUIRE)
                end)
            end)
            p_u_44._evt:fire_event_to_server(v_u_6.EVT_Collection_RegisterCollectionTypeAndID_Client, p_u_70, p_u_71)
        end;
        if v_u_10:does_collection_type_require_playerblob_update(p_u_70) then
            f_confirm_register_will_remove_items(p_u_70, 1, function() --[[ Line: 155 ]]
                --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_29, (ref 3): p_u_44, (ref 4): p_u_45, (ref 5): v_u_6, (copy 6): p_u_70, (ref 7): v_u_43, (ref 8): v_u_10, (ref 9): v_u_5, (copy 10): p_u_71 ]]
                local v_u_76 = p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                p_u_44._evt:wait_on_event_once(v_u_6.EVT_Collection_RegisterCollectionTypeAndID_Server, function(p_u_77) --[[ Line: 149 ]]
                    --[[ Upvalues: (copy 1): v_u_76, (ref 2): p_u_70, (ref 3): p_u_44, (ref 4): v_u_43, (ref 5): p_u_46, (ref 6): v_u_29, (ref 7): p_u_45, (ref 8): v_u_10, (ref 9): v_u_5 ]]
                    local v_u_78 = v_u_76
                    local v_u_79 = p_u_70
                    p_u_44._player_blob_manager:do_sync(function() --[[ Line: 116 ]]
                        --[[ Upvalues: (ref 1): p_u_44, (copy 2): v_u_78, (ref 3): v_u_43, (ref 4): p_u_46, (ref 5): v_u_29, (ref 6): p_u_45, (copy 7): p_u_77, (ref 8): v_u_10, (copy 9): v_u_79, (ref 10): v_u_5 ]]
                        p_u_44._menus:remove_menu(v_u_78)
                        v_u_43 = nil
                        p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Registered!", string.format("Registered %d new %s to your collection.", p_u_77, v_u_10:type_to_name(v_u_79, p_u_77))))
                        p_u_44._sfx_manager:play_sfx(v_u_5.SFX_ACQUIRE)
                    end)
                end)
                p_u_44._evt:fire_event_to_server(v_u_6.EVT_Collection_RegisterCollectionTypeAndID_Client, p_u_70, p_u_71)
            end)
        else
            local v_u_80 = p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_44._evt:wait_on_event_once(v_u_6.EVT_Collection_RegisterCollectionTypeAndID_Server, function(p_u_81) --[[ Line: 149 ]]
                --[[ Upvalues: (copy 1): v_u_80, (copy 2): p_u_70, (ref 3): p_u_44, (ref 4): v_u_43, (ref 5): p_u_46, (ref 6): v_u_29, (ref 7): p_u_45, (ref 8): v_u_10, (ref 9): v_u_5 ]]
                local v_u_82 = v_u_80
                local v_u_83 = p_u_70
                p_u_44._player_blob_manager:do_sync(function() --[[ Line: 116 ]]
                    --[[ Upvalues: (ref 1): p_u_44, (copy 2): v_u_82, (ref 3): v_u_43, (ref 4): p_u_46, (ref 5): v_u_29, (ref 6): p_u_45, (copy 7): p_u_81, (ref 8): v_u_10, (copy 9): v_u_83, (ref 10): v_u_5 ]]
                    p_u_44._menus:remove_menu(v_u_82)
                    v_u_43 = nil
                    p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Registered!", string.format("Registered %d new %s to your collection.", p_u_81, v_u_10:type_to_name(v_u_83, p_u_81))))
                    p_u_44._sfx_manager:play_sfx(v_u_5.SFX_ACQUIRE)
                end)
            end)
            p_u_44._evt:fire_event_to_server(v_u_6.EVT_Collection_RegisterCollectionTypeAndID_Client, p_u_70, p_u_71)
        end;
    end;
    local function f_preview_collection_entry(p_u_84) --[[ Name: preview_collection_entry ]] --[[ Line: 163 ]]
        --[[ Upvalues: (copy 1): p_u_44, (ref 2): v_u_10, (copy 3): p_u_46, (ref 4): v_u_30, (copy 5): p_u_45, (ref 6): v_u_11, (ref 7): v_u_13, (ref 8): v_u_1, (ref 9): v_u_12, (ref 10): v_u_22, (ref 11): v_u_29, (ref 12): v_u_6, (ref 13): v_u_14, (ref 14): v_u_27, (ref 15): v_u_15, (ref 16): v_u_16, (ref 17): v_u_25, (ref 18): v_u_24, (ref 19): v_u_36, (ref 20): v_u_17, (ref 21): v_u_18, (ref 22): v_u_31, (ref 23): v_u_19, (ref 24): v_u_34, (ref 25): v_u_26, (ref 26): v_u_20, (ref 27): v_u_33, (ref 28): v_u_40, (ref 29): v_u_21 ]]
        local v_u_85 = p_u_44._player_blob_manager:get_player_blob()
        if p_u_84:get_collection_type() == v_u_10.Type.Dances then
            local v86 = p_u_46:push_menu(v_u_30:new(p_u_44, p_u_45, p_u_46))
            local v87 = v86:get_character_display()
            v87:push_animation_assetid(v_u_11:singleton():get_dance_assetid_for_id(p_u_84:get_database_id()))
            v87:set_dance_active(true)
            v87:play_selected_animation()
            v86:set_text(string.format("#%d - %s", p_u_84:get_display_collection_id(), p_u_84:get_name()), string.format("Type: %s\nRarity: %s", v_u_13:type_to_string(v_u_11:singleton():get_dance_type_for_id(p_u_84:get_database_id())), v_u_1:enum_val_to_name(v_u_11:singleton():get_dance_rarity_for_id(p_u_84:get_database_id()), v_u_12)))
            local v_u_88 = v86:get_action_buttons():pop_back()
            if v_u_88 then
                v_u_88:set_visible(true)
                local function f_update_button_text() --[[ Name: update_button_text ]] --[[ Line: 183 ]]
                    --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_88, (ref 3): v_u_22, (copy 4): v_u_85, (copy 5): p_u_84 ]]
                    for _, v89 in v_u_1:get_list_of_children_of_classname(v_u_88:get_part(), "TextLabel"):key_itr() do
                        if v_u_22:is_dance_equipped(v_u_85, p_u_84:get_database_id()) then
                            v89.Text = "Unequip Dance"
                        else
                            v89.Text = "Equip Dance"
                        end;
                    end;
                end;
                f_update_button_text()
                v_u_88:bind_data(function() --[[ Line: 194 ]]
                    --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_29, (ref 3): p_u_44, (ref 4): p_u_45, (ref 5): v_u_22, (copy 6): v_u_85, (copy 7): p_u_84, (ref 8): v_u_6, (copy 9): f_update_button_text ]]
                    local v_u_90 = p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                    v_u_22:set_danceid_equipped(v_u_85, p_u_84:get_database_id(), not v_u_22:is_dance_equipped(v_u_85, p_u_84:get_database_id()))
                    v_u_22:validate_playerblob(v_u_85)
                    p_u_44._evt:wait_on_event_once(v_u_6.EVT_PlayerBlob_ServerSetEquippedDancesResponse, function(_) --[[ Line: 199 ]]
                        --[[ Upvalues: (ref 1): p_u_44, (ref 2): f_update_button_text, (copy 3): v_u_90 ]]
                        p_u_44._player_blob_manager:do_sync(function() --[[ Line: 200 ]]
                            --[[ Upvalues: (ref 1): f_update_button_text, (ref 2): p_u_44, (ref 3): v_u_90 ]]
                            f_update_button_text()
                            p_u_44._menus:remove_menu(v_u_90)
                        end)
                    end)
                    p_u_44._evt:fire_event_to_server(v_u_6.EVT_PlayerBlob_ClientSetEquippedDances, p_u_44._player_blob_manager:get_player_blob().DanceEquipped)
                end)
                return;
            end;
        elseif p_u_84:get_collection_type() == v_u_10.Type.Gear then
            local v91 = p_u_46:push_menu(v_u_30:new(p_u_44, p_u_45, p_u_46))
            v_u_14:character_modify_with_equipped_data(v91:get_character_display():get_character(), v_u_27:get_character_model_for_playerid(v_u_1:get_local_userid()), {
                {
                    ["EquipmentID"] = p_u_84:get_database_id(),
                    ["Visible"] = true
                }
            })
            local v_u_92 = v_u_15:singleton():get_equipment_for_id(p_u_84:get_database_id())
            local v93 = v_u_92:get_gear_statmodifierobj()
            local v94 = v_u_16:statsdict_base()
            v_u_16:statsdict_apply_statmodifierobj(v94, v93)
            v91:set_text(string.format("#%d - %s", p_u_84:get_display_collection_id(), p_u_84:get_name()), string.format("Slot: %s\nTier: %d\nElements: %s", v_u_25:slot_to_name(v_u_92:get_avatar_slot()), v_u_92:get_gear_tier(), v_u_16:ranked_color_list_and_statmodifierobj_to_string(v_u_16:statsdict_get_ranked_colors(v94), v93)))
            local v95 = v91:get_action_buttons():pop_back()
            if v95 then
                v95:set_visible(true)
                for _, v96 in v_u_1:get_list_of_children_of_classname(v95:get_part(), "TextLabel"):key_itr() do
                    v96.Text = "Change Appearance"
                end;
                local v_u_97 = v_u_24:playerblob_ownedid_to_equipmentid_dict(v_u_85)
                v95:bind_data(function() --[[ Line: 246 ]]
                    --[[ Upvalues: (ref 1): p_u_44, (ref 2): v_u_36, (ref 3): p_u_45, (ref 4): v_u_15, (copy 5): v_u_97, (ref 6): p_u_46, (ref 7): v_u_29, (copy 8): v_u_92, (ref 9): v_u_6, (copy 10): p_u_84 ]]
                    p_u_44._menus:push_menu(v_u_36:new(p_u_44, p_u_45, p_u_44._menus, function(_, p_u_98) --[[ Line: 251 ]]
                        --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_97, (ref 3): p_u_46, (ref 4): v_u_29, (ref 5): p_u_44, (ref 6): p_u_45, (ref 7): v_u_92, (ref 8): v_u_6, (ref 9): p_u_84 ]]
                        local v99 = v_u_15:singleton():get_equipment_for_id(v_u_97:get(p_u_98))
                        if v99 ~= nil then
                            p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Change Gear Appearance", string.format("Change the appearance of your \'%s\' to look like \'%s\'?", v99:get_name(), v_u_92:get_name()))):set_okay_button_fn(function() --[[ Line: 258 ]]
                                --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_29, (ref 3): p_u_44, (ref 4): p_u_45, (ref 5): v_u_6, (copy 6): p_u_98, (ref 7): p_u_84 ]]
                                local v_u_100 = p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                                p_u_44._evt:wait_on_event_once(v_u_6.EVT_Collection_OverrideGearAppearanceServer, function(_, p_u_101) --[[ Line: 260 ]]
                                    --[[ Upvalues: (ref 1): p_u_44, (copy 2): v_u_100, (ref 3): p_u_46, (ref 4): v_u_29, (ref 5): p_u_45 ]]
                                    p_u_44._player_blob_manager:do_sync(function() --[[ Line: 261 ]]
                                        --[[ Upvalues: (ref 1): p_u_44, (ref 2): v_u_100, (ref 3): p_u_46, (ref 4): v_u_29, (ref 5): p_u_45, (copy 6): p_u_101 ]]
                                        p_u_44._menus:remove_menu(v_u_100)
                                        p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Updated", p_u_101))
                                    end)
                                end)
                                p_u_44._evt:fire_event_to_server(v_u_6.EVT_Collection_OverrideGearAppearanceClient, p_u_98, p_u_84:get_collection_id())
                            end)
                        end;
                    end, function(_, p102) --[[ Line: 269 ]]
                        --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_97, (ref 3): v_u_92 ]]
                        local v103 = v_u_15:singleton():get_equipment_for_id(v_u_97:get(p102))
                        if v103 == nil then
                            return false;
                        else
                            return v_u_92:get_avatar_slot() == v103:get_avatar_slot();
                        end;
                    end))
                end)
                return;
            end;
        else
            if p_u_84:get_collection_type() == v_u_10.Type.Minis then
                local v104 = p_u_46:push_menu(v_u_30:new(p_u_44, p_u_45, p_u_46))
                local v105 = v_u_17:singleton():get_data_for_petid(p_u_84:get_database_id())
                local v_u_106 = v104:get_character_display()
                v_u_106:set_character_visible(false)
                v105:create_character(v_u_17.DEFAULT_CREATE_PET_PARAMS, v_u_106:get_character_parent(), function(p107) --[[ Line: 283 ]]
                    --[[ Upvalues: (copy 1): v_u_106 ]]
                    v_u_106:replace_character_model(p107)
                    v_u_106:set_camera_focus_offset(Vector3.new(0, 0.25, 0))
                    v_u_106:set_camera_height(0.8)
                    v_u_106:set_camera_radius(2.5)
                end)
                local v108 = v_u_17:singleton():get_data_for_petid(p_u_84:get_database_id())
                v104:set_text(string.format("#%d - %s", p_u_84:get_display_collection_id(), p_u_84:get_name()), string.format("Rarity: %s\nElements: %s\nDescription: %s", v_u_1:enum_val_to_name(v108:get_rarity(), v_u_18.Rarity), v_u_16:ranked_color_list_and_statmodifierobj_to_string(v108:get_ranked_colors_list(), v108:get_color_statmodifierobj()), v108:get_description()))
                return;
            end;
            if p_u_84:get_collection_type() == v_u_10.Type.Stages then
                local v109 = p_u_46:push_menu(v_u_31:new(p_u_44, p_u_45, p_u_46))
                local v110 = v_u_19:singleton():get_stage_info_for_id(p_u_84:get_database_id())
                v109:set_text(string.format("Stage: %s", v110:get_name()), "")
                v109:get_image().Image = v110:get_icon()
                local v111 = v109:get_action_buttons():pop_front()
                if v111 then
                    v111:set_visible(true)
                    for _, v112 in v_u_1:get_list_of_children_of_classname(v111:get_part(), "TextLabel"):key_itr() do
                        v112.Text = "Set Stage"
                    end;
                    v111:bind_data(function() --[[ Line: 315 ]]
                        --[[ Upvalues: (ref 1): v_u_34, (copy 2): p_u_84, (ref 3): p_u_44, (ref 4): v_u_26, (ref 5): p_u_46, (ref 6): v_u_29, (ref 7): p_u_45 ]]
                        v_u_34:set_custom_stage_id(p_u_84:get_database_id())
                        p_u_44._player_settings_manager:set_key(v_u_26.Key.SelectedGameStage, p_u_84:get_database_id())
                        local v_u_113 = p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                        p_u_44._player_settings_manager:save_changes_to_playerblob(p_u_44, function() --[[ Line: 319 ]]
                            --[[ Upvalues: (ref 1): p_u_44, (copy 2): v_u_113, (ref 3): p_u_46, (ref 4): v_u_29, (ref 5): p_u_45 ]]
                            p_u_44._menus:remove_menu(v_u_113)
                            p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Stage Set!", "Set as your current stage."))
                        end)
                    end)
                    return;
                end;
            elseif p_u_84:get_collection_type() == v_u_10.Type.Icons then
                local v114 = p_u_46:push_menu(v_u_31:new(p_u_44, p_u_45, p_u_46))
                local v115 = v_u_20:singleton():get_fevericon_for_id(p_u_84:get_database_id())
                v114:set_text(string.format("Icon: %s", v115:get_name()), "")
                v114:get_image().Image = v115:get_image()
                local v_u_116 = v114:get_action_buttons():pop_front()
                if v_u_116 then
                    v_u_116:set_visible(v_u_33:playerblob_get_fevericon(v_u_85) ~= p_u_84:get_database_id())
                    for _, v117 in v_u_1:get_list_of_children_of_classname(v_u_116:get_part(), "TextLabel"):key_itr() do
                        v117.Text = "Set Icon"
                    end;
                    v_u_116:bind_data(function() --[[ Line: 341 ]]
                        --[[ Upvalues: (ref 1): v_u_33, (ref 2): p_u_44, (copy 3): p_u_84, (copy 4): v_u_116 ]]
                        v_u_33:set_selected_fever_icon(p_u_44, p_u_84:get_database_id(), function() --[[ Line: 342 ]]
                            --[[ Upvalues: (ref 1): v_u_116 ]]
                            v_u_116:set_visible(false)
                        end)
                    end)
                    return;
                end;
            elseif p_u_84:get_collection_type() == v_u_10.Type.Songs then
                v_u_40:show_song_info_popup(p_u_44, p_u_84:get_database_id())
                if v_u_21:singleton():contains_key(p_u_84:get_database_id()) then
                    p_u_44._game_join:set_last_loaded_songkey(p_u_84:get_database_id())
                end;
            end;
        end;
    end;
    local function f_show_list_of_collection_type(p_u_118) --[[ Name: show_list_of_collection_type ]] --[[ Line: 357 ]]
        --[[ Upvalues: (copy 1): p_u_44, (ref 2): v_u_8, (ref 3): v_u_9, (copy 4): p_u_45, (copy 5): p_u_46, (ref 6): v_u_10, (copy 7): f_get_collection_type_owned_of_total_string, (copy 8): f_get_collection_info, (ref 9): v_u_42, (ref 10): v_u_1, (copy 11): f_register_collection_type_unregistered, (copy 12): f_preview_collection_entry, (copy 13): f_register_collection_type_collection_id, (ref 14): v_u_2, (ref 15): v_u_3, (ref 16): v_u_4, (ref 17): v_u_35 ]]
        local v_u_119 = ""
        local function f_get_display_string_for_collection_entry(p120) --[[ Name: get_display_string_for_collection_entry ]] --[[ Line: 362 ]]
            --[[ Upvalues: (ref 1): p_u_44, (ref 2): v_u_8 ]]
            local v121 = p_u_44._player_blob_manager:get_player_blob()
            if p_u_44._player_blob_manager:get_cached_collection_info():get_collection_type_and_id_owned(p120:get_collection_type(), p120:get_collection_id()) or (p120:does_playerblob_own_entry(v121) or v_u_8.CollectionDisplayUnowned == true) then
                return string.format("#%d - %s", p120:get_display_collection_id(), p120:get_name());
            else
                return string.format("#%d - ?", p120:get_display_collection_id());
            end;
        end;
        local v_u_140 = v_u_9:new(p_u_44, p_u_45, p_u_46, function(p122) --[[ Line: 377 ]]
            --[[ Upvalues: (ref 1): p_u_44, (ref 2): v_u_10, (copy 3): p_u_118, (ref 4): f_get_collection_type_owned_of_total_string, (ref 5): f_get_collection_info, (ref 6): v_u_42, (ref 7): v_u_119, (copy 8): f_get_display_string_for_collection_entry ]]
            local v123 = p_u_44._player_blob_manager:get_player_blob()
            p122:set_header_text(string.format("Collection: %s", v_u_10:type_to_name(p_u_118)))
            p122:set_sub_text(string.format("Registered: %s", f_get_collection_type_owned_of_total_string(p_u_118)))
            local v124 = p122:get_element_list()
            if v_u_10:get_playerblob_collection_type_collection_info_unregistered_owned_entries_list(v123, p_u_118, f_get_collection_info()):count() > 0 then
                v124:push_back(-1)
            end;
            for _, v125 in v_u_10:collection_type_get_entries_list(p_u_118):key_itr() do
                if v125:should_display_entry() then
                    local v126 = v_u_42 ~= 1 and true or (p_u_44._player_blob_manager:get_cached_collection_info():get_collection_type_and_id_owned(v125:get_collection_type(), v125:get_collection_id()) or v125:does_playerblob_own_entry(v123))
                    if #v_u_119 > 0 and string.find(string.lower((f_get_display_string_for_collection_entry(v125))), v_u_119, 1, true) == nil then
                        v126 = false
                    end;
                    if v126 == true then
                        v124:push_back(v125)
                    end;
                end;
            end;
        end, function(p127, p128, p129, _, p130) --[[ Line: 409 ]]
            --[[ Upvalues: (ref 1): p_u_44, (ref 2): v_u_1, (ref 3): v_u_10, (copy 4): p_u_118, (ref 5): f_get_collection_info, (copy 6): f_get_display_string_for_collection_entry, (ref 7): v_u_8 ]]
            local v131 = p_u_44._player_blob_manager:get_player_blob()
            if p127 == -1 then
                p128.Text = "Register All"
                p129.Image = v_u_1:important_assetid()
                p130:set_select_button_text("Register")
                p130:set_select_button_enabled(true)
                p130:get_description_display().Text = string.format("%d unregistered item(s).", v_u_10:get_playerblob_collection_type_collection_info_unregistered_owned_entries_list(v131, p_u_118, f_get_collection_info()):count())
            else
                local v132
                if typeof(p127) == "table" then
                    v132 = p127.get_collection_id ~= nil
                else
                    v132 = false
                end;
                if v132 then
                    local v133 = p_u_44._player_blob_manager:get_cached_collection_info():get_collection_type_and_id_owned(p127:get_collection_type(), p127:get_collection_id())
                    local v134 = p127:does_playerblob_own_entry(v131)
                    p128.Text = f_get_display_string_for_collection_entry(p127)
                    if v133 or (v134 or v_u_8.CollectionDisplayUnowned == true) then
                        p129.Image = p127:get_icon()
                    else
                        p129.Image = v_u_1:get_question_assetid()
                    end;
                    if v133 then
                        p130:set_select_button_text("Preview")
                        p130:get_description_display().Text = ""
                        p130:set_select_button_enabled(true)
                        return;
                    end;
                    if v133 == false and v134 == true then
                        p130:set_select_button_text("Register")
                        p130:get_description_display().Text = "(Not Registered)"
                        p130:set_select_button_enabled(true)
                        return;
                    end;
                    p130:set_select_button_text("Preview")
                    p130:get_description_display().Text = ""
                    p130:set_select_button_enabled(false)
                end;
            end;
        end, function(p135) --[[ Line: 447 ]]
            --[[ Upvalues: (ref 1): f_register_collection_type_unregistered, (copy 2): p_u_118, (ref 3): p_u_44, (ref 4): f_preview_collection_entry, (ref 5): f_register_collection_type_collection_id ]]
            if p135 == nil then
                return;
            elseif p135 == -1 then
                f_register_collection_type_unregistered(p_u_118)
            else
                local v136
                if typeof(p135) == "table" then
                    v136 = p135.get_collection_id ~= nil
                else
                    v136 = false
                end;
                if v136 then
                    local v137 = p_u_44._player_blob_manager:get_player_blob()
                    local v138 = p_u_44._player_blob_manager:get_cached_collection_info():get_collection_type_and_id_owned(p135:get_collection_type(), p135:get_collection_id())
                    local v139 = p135:does_playerblob_own_entry(v137)
                    if v138 then
                        f_preview_collection_entry(p135)
                        return;
                    end;
                    if v138 == false and v139 == true then
                        f_register_collection_type_collection_id(p135:get_collection_type(), p135:get_collection_id())
                    end;
                end;
            end;
        end):set_close_on_element_select(false):set_refresh_on_refocus(true)
        v_u_140:get_list_adapter():set_do_wrap(true)
        v_u_140:set_settings_section_visible()
        local v_u_141 = v_u_2:new()
        local function f_update_filter_toggles() --[[ Name: update_filter_toggles ]] --[[ Line: 474 ]]
            --[[ Upvalues: (copy 1): v_u_141, (ref 2): v_u_42, (ref 3): v_u_140 ]]
            for v142, v143 in v_u_141:key_itr() do
                v143:set_toggle(v142 == v_u_42)
            end;
            v_u_140:get_list_adapter():reset()
        end;
        local v148 = v_u_3:new():push_back_table_list({ function(p144) --[[ Line: 482 ]]
                --[[ Upvalues: (ref 1): v_u_42, (copy 2): f_update_filter_toggles, (ref 3): v_u_140, (ref 4): v_u_4, (copy 5): v_u_141 ]]
                p144:bind_data(function() --[[ Line: 484 ]]
                    --[[ Upvalues: (ref 1): v_u_42, (ref 2): f_update_filter_toggles, (ref 3): v_u_140 ]]
                    v_u_42 = 1
                    f_update_filter_toggles()
                    v_u_140:refresh()
                end)
                v_u_4:set_button_text(p144, "Show Owned")
                v_u_141:add(1, v_u_4:button_bind_anim_toggle(p144, function() --[[ Line: 490 ]]
                    --[[ Upvalues: (ref 1): v_u_140 ]]
                    return v_u_140:get_alpha();
                end))
            end, function(p145) --[[ Line: 492 ]]
                --[[ Upvalues: (ref 1): v_u_42, (copy 2): f_update_filter_toggles, (ref 3): v_u_140, (ref 4): v_u_4, (copy 5): v_u_141 ]]
                p145:bind_data(function() --[[ Line: 494 ]]
                    --[[ Upvalues: (ref 1): v_u_42, (ref 2): f_update_filter_toggles, (ref 3): v_u_140 ]]
                    v_u_42 = 2
                    f_update_filter_toggles()
                    v_u_140:refresh()
                end)
                v_u_4:set_button_text(p145, "Show All")
                v_u_141:add(2, v_u_4:button_bind_anim_toggle(p145, function() --[[ Line: 500 ]]
                    --[[ Upvalues: (ref 1): v_u_140 ]]
                    return v_u_140:get_alpha();
                end))
            end, function(p146) --[[ Line: 502 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): p_u_44, (ref 3): v_u_35, (ref 4): p_u_45, (ref 5): p_u_46, (ref 6): v_u_119, (copy 7): f_update_filter_toggles, (ref 8): v_u_140 ]]
                v_u_4:set_button_text(p146, "Search Filter")
                p146:bind_data(function() --[[ Line: 504 ]]
                    --[[ Upvalues: (ref 1): p_u_44, (ref 2): v_u_35, (ref 3): p_u_45, (ref 4): p_u_46, (ref 5): v_u_119, (ref 6): f_update_filter_toggles, (ref 7): v_u_140 ]]
                    p_u_44._menus:push_menu(v_u_35:new(p_u_44, p_u_45, p_u_46, "Search", "Enter search filter:", function(p147) --[[ Line: 505 ]]
                        --[[ Upvalues: (ref 1): v_u_119, (ref 2): f_update_filter_toggles, (ref 3): v_u_140 ]]
                        if typeof(p147) == "string" then
                            v_u_119 = ""
                            f_update_filter_toggles()
                            v_u_119 = string.lower(p147)
                            v_u_140:refresh()
                        end;
                    end):set_empty_message("(Text)"))
                end)
            end })
        local v149 = v_u_140
        for _, v150 in v_u_140:get_settings_buttons():key_itr() do
            if v148:count() > 0 then
                v150:set_visible(true)
                v148:pop_front()(v150)
            else
                v150:set_visible(false)
            end;
        end;
        f_update_filter_toggles()
        p_u_46:push_menu(v149)
    end;
    local function f_leaderboard_entry_to_display_string(p151) --[[ Name: leaderboard_entry_to_display_string ]] --[[ Line: 533 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_10 ]]
        local v152 = string.format("TOTAL - %s Point(s)\n", v_u_1:comma_value(p151:get_overall_point_amount()))
        for _, v153 in v_u_10:get_collection_types_display_order_list():key_itr() do
            v152 = v152 .. string.format("From %s: %s Point(s)\n", v_u_10:type_to_name(v153), v_u_1:comma_value(p151:get_type_point_amount(v153)))
        end;
        return v152;
    end;
    local function _() --[[ Name: show_collection_points_leaderboard_menu ]] --[[ Line: 541 ]]
        --[[ Upvalues: (copy 1): p_u_46, (ref 2): v_u_29, (copy 3): p_u_44, (copy 4): p_u_45, (ref 5): v_u_6, (ref 6): v_u_10, (ref 7): v_u_1, (ref 8): v_u_9, (ref 9): v_u_43, (copy 10): f_leaderboard_entry_to_display_string, (ref 11): v_u_23 ]]
        local v_u_154 = p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
        p_u_44._evt:wait_on_event_once(v_u_6.EVT_Collection_GetLeaderboardServer, function(p155, p156) --[[ Line: 543 ]]
            --[[ Upvalues: (ref 1): p_u_44, (copy 2): v_u_154, (ref 3): v_u_10, (ref 4): v_u_1, (ref 5): p_u_46, (ref 6): v_u_9, (ref 7): p_u_45, (ref 8): v_u_43, (ref 9): v_u_29, (ref 10): f_leaderboard_entry_to_display_string, (ref 11): v_u_23 ]]
            p_u_44._menus:remove_menu(v_u_154)
            local v_u_157 = v_u_10.CollectionLeaderboardEntry:table_to_list(p155)
            local v_u_158 = v_u_10.CollectionLeaderboardRankData:from_table(p156)
            local function f_rank_val_to_str(p159) --[[ Name: rank_val_to_str ]] --[[ Line: 547 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return (p159 == nil or p159 <= 0) and "-" or v_u_1:num_placify(p159);
            end;
            p_u_46:push_menu(v_u_9:new(p_u_44, p_u_45, p_u_46, function(p160) --[[ Line: 556 ]]
                --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_1, (copy 3): v_u_158, (copy 4): v_u_157 ]]
                p160:set_header_text(string.format("Leaderboards"))
                if v_u_43 ~= nil then
                    p160:set_sub_text(string.format("Your Total: %s", v_u_1:comma_value(v_u_43:get_overall_point_amount())))
                end;
                p160:get_element_list():push_back(v_u_158)
                p160:get_element_list():push_back_from_list(v_u_157)
            end, function(p_u_161, p162, p_u_163, _, p_u_164, p165, _) --[[ Line: 567 ]]
                --[[ Upvalues: (copy 1): v_u_158, (ref 2): v_u_1 ]]
                if p_u_161 == v_u_158 then
                    p162.Text = "Your Rank"
                    p_u_163.Image = v_u_1:important_assetid()
                    local v166 = p_u_164:get_description_display()
                    local v167 = v_u_158:get_overall_rank()
                    v166.Text = "Overall: " .. ((v167 == nil or v167 <= 0) and "-" or v_u_1:num_placify(v167))
                else
                    p162.Text = string.format("[%d] %s", p165 - 1, p_u_161:get_player_name())
                    p_u_163.Image = v_u_1:transparent_assetid()
                    p_u_164:get_description_display().Text = string.format("Total: %s", v_u_1:comma_value(p_u_161:get_overall_point_amount()))
                    v_u_1:get_user_thumbnail(p_u_161:get_player_id(), function(p168) --[[ Line: 579 ]]
                        --[[ Upvalues: (copy 1): p_u_164, (copy 2): p_u_161, (copy 3): p_u_163 ]]
                        if p_u_164:get_data() == p_u_161 then
                            p_u_163.Image = p168
                        end;
                    end, false)
                end;
            end, function(p169) --[[ Line: 588 ]]
                --[[ Upvalues: (copy 1): v_u_158, (copy 2): f_rank_val_to_str, (ref 3): v_u_10, (ref 4): p_u_46, (ref 5): v_u_29, (ref 6): p_u_44, (ref 7): p_u_45, (ref 8): f_leaderboard_entry_to_display_string ]]
                if p169 == nil then
                    return;
                elseif p169 == v_u_158 then
                    p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Your Rank", ((function(p170) --[[ Name: rank_data_to_display_string ]] --[[ Line: 591 ]]
                        --[[ Upvalues: (ref 1): f_rank_val_to_str, (ref 2): v_u_10 ]]
                        local v171 = "" .. string.format("Overall Rank: %s\n", f_rank_val_to_str(p170:get_overall_rank()))
                        for _, v172 in v_u_10:get_collection_types_display_order_list():key_itr() do
                            v171 = v171 .. string.format("%s: %s\n", v_u_10:type_to_name(v172), f_rank_val_to_str(p170:get_category_to_rank():get(v172)))
                        end;
                        return v171;
                    end)(p169))))
                else
                    p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text(string.format("%s\'s Collection", p169:get_player_name()), (f_leaderboard_entry_to_display_string(p169))))
                end;
            end)):set_close_on_element_select(false):set_fn_info_button_pressed(function() --[[ Line: 624 ]]
                --[[ Upvalues: (ref 1): p_u_44, (ref 2): v_u_29, (ref 3): v_u_23 ]]
                p_u_44._menus:push_menu(v_u_29:new(p_u_44, p_u_44._spui, p_u_44._menus):set_text("Collection Point Leaderboard", string.format("Here\'s who collectected them all...\nView the top %d players by collection points here!", v_u_23.COLLECTION_LEADERBOARD_ENTRY_COUNT)))
            end):get_list_adapter():set_do_wrap(true)
        end)
        p_u_44._evt:fire_event_to_server(v_u_6.EVT_Collection_GetLeaderboardClient)
    end;
    local function _() --[[ Name: show_check_collection_points_menu ]] --[[ Line: 636 ]]
        --[[ Upvalues: (copy 1): p_u_46, (ref 2): v_u_29, (copy 3): p_u_44, (copy 4): p_u_45, (ref 5): v_u_6, (ref 6): v_u_43, (ref 7): v_u_10, (copy 8): f_leaderboard_entry_to_display_string, (ref 9): v_u_1, (ref 10): v_u_9, (ref 11): v_u_23, (ref 12): v_u_8, (ref 13): v_u_38, (ref 14): v_u_39, (ref 15): v_u_37 ]]
        local v_u_173 = p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
        p_u_44._evt:wait_on_event_once(v_u_6.EVT_Collection_CheckPointsServer, function(p_u_174, p_u_175) --[[ Line: 638 ]]
            --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_10, (ref 3): p_u_46, (ref 4): v_u_29, (ref 5): p_u_44, (ref 6): p_u_45, (ref 7): f_leaderboard_entry_to_display_string, (ref 8): v_u_6, (ref 9): v_u_1, (ref 10): v_u_9, (ref 11): v_u_23, (copy 12): v_u_173, (ref 13): v_u_8, (ref 14): v_u_38, (ref 15): v_u_39, (ref 16): v_u_37 ]]
            local function f_show_entry_results() --[[ Name: show_entry_results ]] --[[ Line: 639 ]]
                --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_10, (copy 3): p_u_174, (ref 4): p_u_46, (ref 5): v_u_29, (ref 6): p_u_44, (ref 7): p_u_45, (ref 8): f_leaderboard_entry_to_display_string, (ref 9): v_u_6, (ref 10): v_u_1, (ref 11): v_u_9, (ref 12): v_u_23 ]]
                v_u_43 = v_u_10.CollectionLeaderboardEntry:from_table(p_u_174)
                p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Your Collection Points", string.format("%s\nPress \"Okay\" to view the leaderboards.", (f_leaderboard_entry_to_display_string(v_u_43)))):set_okay_button_fn(function() --[[ Line: 647 ]]
                    --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_29, (ref 3): p_u_44, (ref 4): p_u_45, (ref 5): v_u_6, (ref 6): v_u_10, (ref 7): v_u_1, (ref 8): v_u_9, (ref 9): v_u_43, (ref 10): f_leaderboard_entry_to_display_string, (ref 11): v_u_23 ]]
                    local v_u_176 = p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                    p_u_44._evt:wait_on_event_once(v_u_6.EVT_Collection_GetLeaderboardServer, function(p177, p178) --[[ Line: 543 ]]
                        --[[ Upvalues: (ref 1): p_u_44, (copy 2): v_u_176, (ref 3): v_u_10, (ref 4): v_u_1, (ref 5): p_u_46, (ref 6): v_u_9, (ref 7): p_u_45, (ref 8): v_u_43, (ref 9): v_u_29, (ref 10): f_leaderboard_entry_to_display_string, (ref 11): v_u_23 ]]
                        p_u_44._menus:remove_menu(v_u_176)
                        local v_u_179 = v_u_10.CollectionLeaderboardEntry:table_to_list(p177)
                        local v_u_180 = v_u_10.CollectionLeaderboardRankData:from_table(p178)
                        local function f_rank_val_to_str(p181) --[[ Name: rank_val_to_str ]] --[[ Line: 547 ]]
                            --[[ Upvalues: (ref 1): v_u_1 ]]
                            return (p181 == nil or p181 <= 0) and "-" or v_u_1:num_placify(p181);
                        end;
                        p_u_46:push_menu(v_u_9:new(p_u_44, p_u_45, p_u_46, function(p182) --[[ Line: 556 ]]
                            --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_1, (copy 3): v_u_180, (copy 4): v_u_179 ]]
                            p182:set_header_text(string.format("Leaderboards"))
                            if v_u_43 ~= nil then
                                p182:set_sub_text(string.format("Your Total: %s", v_u_1:comma_value(v_u_43:get_overall_point_amount())))
                            end;
                            p182:get_element_list():push_back(v_u_180)
                            p182:get_element_list():push_back_from_list(v_u_179)
                        end, function(p_u_183, p184, p_u_185, _, p_u_186, p187, _) --[[ Line: 567 ]]
                            --[[ Upvalues: (copy 1): v_u_180, (ref 2): v_u_1 ]]
                            if p_u_183 == v_u_180 then
                                p184.Text = "Your Rank"
                                p_u_185.Image = v_u_1:important_assetid()
                                local v188 = p_u_186:get_description_display()
                                local v189 = v_u_180:get_overall_rank()
                                v188.Text = "Overall: " .. ((v189 == nil or v189 <= 0) and "-" or v_u_1:num_placify(v189))
                            else
                                p184.Text = string.format("[%d] %s", p187 - 1, p_u_183:get_player_name())
                                p_u_185.Image = v_u_1:transparent_assetid()
                                p_u_186:get_description_display().Text = string.format("Total: %s", v_u_1:comma_value(p_u_183:get_overall_point_amount()))
                                v_u_1:get_user_thumbnail(p_u_183:get_player_id(), function(p190) --[[ Line: 579 ]]
                                    --[[ Upvalues: (copy 1): p_u_186, (copy 2): p_u_183, (copy 3): p_u_185 ]]
                                    if p_u_186:get_data() == p_u_183 then
                                        p_u_185.Image = p190
                                    end;
                                end, false)
                            end;
                        end, function(p191) --[[ Line: 588 ]]
                            --[[ Upvalues: (copy 1): v_u_180, (copy 2): f_rank_val_to_str, (ref 3): v_u_10, (ref 4): p_u_46, (ref 5): v_u_29, (ref 6): p_u_44, (ref 7): p_u_45, (ref 8): f_leaderboard_entry_to_display_string ]]
                            if p191 == nil then
                                return;
                            elseif p191 == v_u_180 then
                                p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Your Rank", ((function(p192) --[[ Name: rank_data_to_display_string ]] --[[ Line: 591 ]]
                                    --[[ Upvalues: (ref 1): f_rank_val_to_str, (ref 2): v_u_10 ]]
                                    local v193 = "" .. string.format("Overall Rank: %s\n", f_rank_val_to_str(p192:get_overall_rank()))
                                    for _, v194 in v_u_10:get_collection_types_display_order_list():key_itr() do
                                        v193 = v193 .. string.format("%s: %s\n", v_u_10:type_to_name(v194), f_rank_val_to_str(p192:get_category_to_rank():get(v194)))
                                    end;
                                    return v193;
                                end)(p191))))
                            else
                                p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text(string.format("%s\'s Collection", p191:get_player_name()), (f_leaderboard_entry_to_display_string(p191))))
                            end;
                        end)):set_close_on_element_select(false):set_fn_info_button_pressed(function() --[[ Line: 624 ]]
                            --[[ Upvalues: (ref 1): p_u_44, (ref 2): v_u_29, (ref 3): v_u_23 ]]
                            p_u_44._menus:push_menu(v_u_29:new(p_u_44, p_u_44._spui, p_u_44._menus):set_text("Collection Point Leaderboard", string.format("Here\'s who collectected them all...\nView the top %d players by collection points here!", v_u_23.COLLECTION_LEADERBOARD_ENTRY_COUNT)))
                        end):get_list_adapter():set_do_wrap(true)
                    end)
                    p_u_44._evt:fire_event_to_server(v_u_6.EVT_Collection_GetLeaderboardClient)
                end))
            end;
            if p_u_175 == nil or #p_u_175 == 0 then
                p_u_44._menus:remove_menu(v_u_173)
                f_show_entry_results()
            else
                p_u_44._player_blob_manager:do_sync(function() --[[ Line: 657 ]]
                    --[[ Upvalues: (ref 1): p_u_44, (ref 2): v_u_173, (ref 3): v_u_8, (ref 4): p_u_46, (ref 5): v_u_38, (ref 6): p_u_45, (ref 7): v_u_39, (copy 8): p_u_175, (copy 9): f_show_entry_results, (ref 10): v_u_37 ]]
                    p_u_44._menus:remove_menu(v_u_173)
                    if v_u_8.UseRewardDescriptionInfoAcquiredUI == true then
                        p_u_46:push_menu(v_u_38:new(p_u_44, p_u_45, p_u_46, v_u_39.RewardInfo:table_to_list(p_u_175), function() --[[ Line: 661 ]]
                            --[[ Upvalues: (ref 1): f_show_entry_results ]]
                            f_show_entry_results()
                        end))
                    else
                        p_u_46:push_menu(v_u_37:new(p_u_44, p_u_45, p_u_46, v_u_39.RewardInfo:table_to_list(p_u_175), function() --[[ Line: 671 ]]
                            --[[ Upvalues: (ref 1): f_show_entry_results ]]
                            f_show_entry_results()
                        end))
                    end;
                end)
            end;
        end)
        p_u_44._evt:fire_event_to_server(v_u_6.EVT_Collection_CheckPointsClient)
    end;
    p_u_46:push_menu(v_u_9:new(p_u_44, p_u_45, p_u_46, function(p195) --[[ Line: 686 ]]
        --[[ Upvalues: (ref 1): v_u_10 ]]
        p195:set_header_text(string.format("My Collection"))
        p195:set_sub_text("")
        local v196 = p195:get_element_list()
        v196:push_back(-1)
        for _, v197 in v_u_10:get_collection_types_display_order_list():key_itr() do
            v196:push_back(v197)
        end;
    end, function(p198, p199, p200, _, p201) --[[ Line: 695 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_43, (ref 3): v_u_7, (ref 4): v_u_10, (copy 5): p_u_44 ]]
        if p198 == -1 then
            p199.Text = "Check Collection Points"
            p200.Image = v_u_1:important_assetid()
            if v_u_43 == nil then
                p201:get_description_display().Text = ""
            else
                p201:get_description_display().Text = string.format("%s Points", v_u_1:comma_value(v_u_43:get_overall_point_amount()))
            end;
        else
            if v_u_7:test_enum_member(p198, v_u_10.Type) then
                p199.Text = string.format("%s", v_u_10:type_to_name(p198))
                p201:get_description_display().Text = string.format("%d / %d", p_u_44._player_blob_manager:get_cached_collection_info():get_collection_type_owned_count(p198), v_u_10:get_collection_type_display_entry_count(p198))
                p200.Image = v_u_10:type_to_icon(p198)
            end;
            return;
        end;
    end, function(p202) --[[ Line: 712 ]]
        --[[ Upvalues: (copy 1): p_u_46, (ref 2): v_u_29, (copy 3): p_u_44, (copy 4): p_u_45, (ref 5): v_u_6, (ref 6): v_u_43, (ref 7): v_u_10, (copy 8): f_leaderboard_entry_to_display_string, (ref 9): v_u_1, (ref 10): v_u_9, (ref 11): v_u_23, (ref 12): v_u_8, (ref 13): v_u_38, (ref 14): v_u_39, (ref 15): v_u_37, (ref 16): v_u_7, (copy 17): f_show_list_of_collection_type ]]
        if p202 == nil then
            return;
        elseif p202 == -1 then
            local v_u_203 = p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_44._evt:wait_on_event_once(v_u_6.EVT_Collection_CheckPointsServer, function(p_u_204, p_u_205) --[[ Line: 638 ]]
                --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_10, (ref 3): p_u_46, (ref 4): v_u_29, (ref 5): p_u_44, (ref 6): p_u_45, (ref 7): f_leaderboard_entry_to_display_string, (ref 8): v_u_6, (ref 9): v_u_1, (ref 10): v_u_9, (ref 11): v_u_23, (copy 12): v_u_203, (ref 13): v_u_8, (ref 14): v_u_38, (ref 15): v_u_39, (ref 16): v_u_37 ]]
                local function f_show_entry_results() --[[ Name: show_entry_results ]] --[[ Line: 639 ]]
                    --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_10, (copy 3): p_u_204, (ref 4): p_u_46, (ref 5): v_u_29, (ref 6): p_u_44, (ref 7): p_u_45, (ref 8): f_leaderboard_entry_to_display_string, (ref 9): v_u_6, (ref 10): v_u_1, (ref 11): v_u_9, (ref 12): v_u_23 ]]
                    v_u_43 = v_u_10.CollectionLeaderboardEntry:from_table(p_u_204)
                    p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Your Collection Points", string.format("%s\nPress \"Okay\" to view the leaderboards.", (f_leaderboard_entry_to_display_string(v_u_43)))):set_okay_button_fn(function() --[[ Line: 647 ]]
                        --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_29, (ref 3): p_u_44, (ref 4): p_u_45, (ref 5): v_u_6, (ref 6): v_u_10, (ref 7): v_u_1, (ref 8): v_u_9, (ref 9): v_u_43, (ref 10): f_leaderboard_entry_to_display_string, (ref 11): v_u_23 ]]
                        local v_u_206 = p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                        p_u_44._evt:wait_on_event_once(v_u_6.EVT_Collection_GetLeaderboardServer, function(p207, p208) --[[ Line: 543 ]]
                            --[[ Upvalues: (ref 1): p_u_44, (copy 2): v_u_206, (ref 3): v_u_10, (ref 4): v_u_1, (ref 5): p_u_46, (ref 6): v_u_9, (ref 7): p_u_45, (ref 8): v_u_43, (ref 9): v_u_29, (ref 10): f_leaderboard_entry_to_display_string, (ref 11): v_u_23 ]]
                            p_u_44._menus:remove_menu(v_u_206)
                            local v_u_209 = v_u_10.CollectionLeaderboardEntry:table_to_list(p207)
                            local v_u_210 = v_u_10.CollectionLeaderboardRankData:from_table(p208)
                            local function f_rank_val_to_str(p211) --[[ Name: rank_val_to_str ]] --[[ Line: 547 ]]
                                --[[ Upvalues: (ref 1): v_u_1 ]]
                                return (p211 == nil or p211 <= 0) and "-" or v_u_1:num_placify(p211);
                            end;
                            p_u_46:push_menu(v_u_9:new(p_u_44, p_u_45, p_u_46, function(p212) --[[ Line: 556 ]]
                                --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_1, (copy 3): v_u_210, (copy 4): v_u_209 ]]
                                p212:set_header_text(string.format("Leaderboards"))
                                if v_u_43 ~= nil then
                                    p212:set_sub_text(string.format("Your Total: %s", v_u_1:comma_value(v_u_43:get_overall_point_amount())))
                                end;
                                p212:get_element_list():push_back(v_u_210)
                                p212:get_element_list():push_back_from_list(v_u_209)
                            end, function(p_u_213, p214, p_u_215, _, p_u_216, p217, _) --[[ Line: 567 ]]
                                --[[ Upvalues: (copy 1): v_u_210, (ref 2): v_u_1 ]]
                                if p_u_213 == v_u_210 then
                                    p214.Text = "Your Rank"
                                    p_u_215.Image = v_u_1:important_assetid()
                                    local v218 = p_u_216:get_description_display()
                                    local v219 = v_u_210:get_overall_rank()
                                    v218.Text = "Overall: " .. ((v219 == nil or v219 <= 0) and "-" or v_u_1:num_placify(v219))
                                else
                                    p214.Text = string.format("[%d] %s", p217 - 1, p_u_213:get_player_name())
                                    p_u_215.Image = v_u_1:transparent_assetid()
                                    p_u_216:get_description_display().Text = string.format("Total: %s", v_u_1:comma_value(p_u_213:get_overall_point_amount()))
                                    v_u_1:get_user_thumbnail(p_u_213:get_player_id(), function(p220) --[[ Line: 579 ]]
                                        --[[ Upvalues: (copy 1): p_u_216, (copy 2): p_u_213, (copy 3): p_u_215 ]]
                                        if p_u_216:get_data() == p_u_213 then
                                            p_u_215.Image = p220
                                        end;
                                    end, false)
                                end;
                            end, function(p221) --[[ Line: 588 ]]
                                --[[ Upvalues: (copy 1): v_u_210, (copy 2): f_rank_val_to_str, (ref 3): v_u_10, (ref 4): p_u_46, (ref 5): v_u_29, (ref 6): p_u_44, (ref 7): p_u_45, (ref 8): f_leaderboard_entry_to_display_string ]]
                                if p221 == nil then
                                    return;
                                elseif p221 == v_u_210 then
                                    p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text("Your Rank", ((function(p222) --[[ Name: rank_data_to_display_string ]] --[[ Line: 591 ]]
                                        --[[ Upvalues: (ref 1): f_rank_val_to_str, (ref 2): v_u_10 ]]
                                        local v223 = "" .. string.format("Overall Rank: %s\n", f_rank_val_to_str(p222:get_overall_rank()))
                                        for _, v224 in v_u_10:get_collection_types_display_order_list():key_itr() do
                                            v223 = v223 .. string.format("%s: %s\n", v_u_10:type_to_name(v224), f_rank_val_to_str(p222:get_category_to_rank():get(v224)))
                                        end;
                                        return v223;
                                    end)(p221))))
                                else
                                    p_u_46:push_menu(v_u_29:new(p_u_44, p_u_45, p_u_46):set_text(string.format("%s\'s Collection", p221:get_player_name()), (f_leaderboard_entry_to_display_string(p221))))
                                end;
                            end)):set_close_on_element_select(false):set_fn_info_button_pressed(function() --[[ Line: 624 ]]
                                --[[ Upvalues: (ref 1): p_u_44, (ref 2): v_u_29, (ref 3): v_u_23 ]]
                                p_u_44._menus:push_menu(v_u_29:new(p_u_44, p_u_44._spui, p_u_44._menus):set_text("Collection Point Leaderboard", string.format("Here\'s who collectected them all...\nView the top %d players by collection points here!", v_u_23.COLLECTION_LEADERBOARD_ENTRY_COUNT)))
                            end):get_list_adapter():set_do_wrap(true)
                        end)
                        p_u_44._evt:fire_event_to_server(v_u_6.EVT_Collection_GetLeaderboardClient)
                    end))
                end;
                if p_u_205 == nil or #p_u_205 == 0 then
                    p_u_44._menus:remove_menu(v_u_203)
                    f_show_entry_results()
                else
                    p_u_44._player_blob_manager:do_sync(function() --[[ Line: 657 ]]
                        --[[ Upvalues: (ref 1): p_u_44, (ref 2): v_u_203, (ref 3): v_u_8, (ref 4): p_u_46, (ref 5): v_u_38, (ref 6): p_u_45, (ref 7): v_u_39, (copy 8): p_u_205, (copy 9): f_show_entry_results, (ref 10): v_u_37 ]]
                        p_u_44._menus:remove_menu(v_u_203)
                        if v_u_8.UseRewardDescriptionInfoAcquiredUI == true then
                            p_u_46:push_menu(v_u_38:new(p_u_44, p_u_45, p_u_46, v_u_39.RewardInfo:table_to_list(p_u_205), function() --[[ Line: 661 ]]
                                --[[ Upvalues: (ref 1): f_show_entry_results ]]
                                f_show_entry_results()
                            end))
                        else
                            p_u_46:push_menu(v_u_37:new(p_u_44, p_u_45, p_u_46, v_u_39.RewardInfo:table_to_list(p_u_205), function() --[[ Line: 671 ]]
                                --[[ Upvalues: (ref 1): f_show_entry_results ]]
                                f_show_entry_results()
                            end))
                        end;
                    end)
                end;
            end)
            p_u_44._evt:fire_event_to_server(v_u_6.EVT_Collection_CheckPointsClient)
        elseif v_u_7:test_enum_member(p202, v_u_10.Type) then
            f_show_list_of_collection_type(p202)
        end;
    end):set_close_on_element_select(false):set_refresh_on_refocus(true):set_fn_info_button_pressed(function() --[[ Line: 724 ]]
        --[[ Upvalues: (copy 1): p_u_44, (ref 2): v_u_29 ]]
        p_u_44._menus:push_menu(v_u_29:new(p_u_44, p_u_44._spui, p_u_44._menus):set_text("My Collection", "Gotta collect them all! Add collectables to your log and track your progress. You will be able to preview and access any item in your collection once registered."))
    end))
end;
return v41;
