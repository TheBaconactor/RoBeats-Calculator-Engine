-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:57 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_8 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_9 = require(game.ReplicatedStorage.Avatar.PlayerBlobLoadout)
local v_u_10 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_11 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_12 = require(game.ReplicatedStorage.Pets.PetUtils)
local v_u_13 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_14 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_15 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_16 = require(game.ReplicatedStorage.LocalShared.PurchaseRedirect)
local v_u_17 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_18 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_19 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v20 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_21 = nil
local v_u_22 = nil
v20:require_client(function() --[[ Line: 30 ]]
    --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_22 ]]
    v_u_21 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_22 = require(game.ReplicatedStorage.Lobby.Menus.TextInputUI)
end)
return {
    ["new"] = function(_, p_u_23, p_u_24, p_u_25, p_u_26, p_u_27) --[[ Name: new ]] --[[ Line: 37 ]]
        --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_13, (copy 3): v_u_3, (copy 4): v_u_5, (copy 5): v_u_4, (copy 6): v_u_7, (copy 7): v_u_14, (copy 8): v_u_15, (copy 9): v_u_17, (copy 10): v_u_18, (copy 11): v_u_16, (ref 12): v_u_21, (copy 13): v_u_1, (ref 14): v_u_22, (copy 15): v_u_6, (copy 16): v_u_19, (copy 17): v_u_10, (copy 18): v_u_11, (copy 19): v_u_8, (copy 20): v_u_12, (copy 21): v_u_2 ]]
        local v_u_28 = {}
        local v_u_29 = v_u_9:invalid_loadout_index()
        local v_u_30 = false
        v_u_28.has_loadout_change = function(_) --[[ Name: has_loadout_change ]] --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): v_u_30 ]]
            return v_u_30;
        end;
        local v_u_31 = nil
        local v_u_32 = nil
        local v_u_33 = nil
        local v_u_41 = v_u_13:new():set_fn_get_data_list(function() --[[ Line: 47 ]]
            --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_9, (ref 3): v_u_3 ]]
            local v34 = v_u_9:get_loadout_index_range((p_u_23._player_blob_manager:get_player_blob()))
            local v35 = v_u_3:new()
            for v36 = v34:min(), v34:max() do
                v35:push_back(v36)
            end;
            return v35;
        end):set_fn_set_element_data(function(p37, p38, _, _) --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            if p38 == nil then
                p37:set_loadout_index(v_u_9:invalid_loadout_index())
            else
                p37:set_loadout_index(p38)
            end;
        end):set_fn_next_prev_visible(function(p39, p40) --[[ Line: 63 ]]
            --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_32 ]]
            v_u_33:set_visible(p39)
            v_u_32:set_visible(p40)
        end)
        local function f_cons() --[[ Name: cons ]] --[[ Line: 68 ]]
            --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_27, (copy 3): p_u_23, (ref 4): v_u_5, (ref 5): v_u_4, (copy 6): p_u_26, (copy 7): p_u_24, (ref 8): v_u_7, (ref 9): v_u_29, (copy 10): v_u_28, (ref 11): v_u_33, (copy 12): v_u_41, (ref 13): v_u_32, (ref 14): v_u_3, (ref 15): v_u_31, (copy 16): p_u_25, (ref 17): v_u_14, (ref 18): v_u_15, (ref 19): v_u_17, (ref 20): v_u_18, (ref 21): v_u_16, (ref 22): v_u_21, (ref 23): v_u_1, (ref 24): v_u_22, (ref 25): v_u_6, (ref 26): v_u_19 ]]
            local function f_create_loadout_button(p42) --[[ Name: create_loadout_button ]] --[[ Line: 69 ]]
                --[[ Upvalues: (ref 1): v_u_9, (ref 2): p_u_27, (ref 3): p_u_23, (ref 4): v_u_5, (ref 5): v_u_4, (ref 6): p_u_26, (ref 7): p_u_24, (ref 8): v_u_7, (ref 9): v_u_29, (ref 10): v_u_28 ]]
                local v_u_43 = v_u_9:invalid_loadout_index()
                local v44 = p_u_27:add_cycle_element(p_u_23, 1, v_u_5:new(v_u_4:new(p_u_27, p_u_26.PrimaryPart, p42.PrimaryPart), p_u_24, function() --[[ Line: 74 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_7, (ref 3): v_u_43, (ref 4): v_u_29, (ref 5): v_u_9, (ref 6): v_u_28 ]]
                    p_u_23._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                    if v_u_43 == v_u_29 then
                        v_u_29 = v_u_9:invalid_loadout_index()
                    else
                        v_u_29 = v_u_43
                    end;
                    v_u_28:on_updated_loadout_index()
                end):set_auto_zoffset_behaviour(true))
                local l_Frame_0 = p42.PrimaryPart.SurfaceGui.Frame
                local l_LoadoutNameDisplay_0 = l_Frame_0.LoadoutNameDisplay
                local v45 = {
                    ["Button"] = v44,
                    ["GearPowerDisplay"] = l_Frame_0.GearPowerDisplay,
                    ["PrimaryColorIcon"] = l_Frame_0.ColorSection.PrimaryColorIcon,
                    ["SecondaryColorIcon"] = l_Frame_0.ColorSection.SecondaryColorIcon,
                    ["Toggle"] = v_u_5:button_bind_anim_toggle(v44, function() --[[ Line: 92 ]]
                        --[[ Upvalues: (ref 1): p_u_27 ]]
                        return p_u_27:get_alpha();
                    end),
                    ["get_loadout_index"] = function(_) --[[ Name: get_loadout_index ]] --[[ Line: 96 ]]
                        --[[ Upvalues: (ref 1): v_u_43 ]]
                        return v_u_43;
                    end
                }
                v45.Toggle:set_toggle(false)
                v45.set_loadout_index = function(_, p46) --[[ Name: set_loadout_index ]] --[[ Line: 98 ]]
                    --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_9, (copy 3): l_LoadoutNameDisplay_0, (ref 4): p_u_23 ]]
                    v_u_43 = p46
                    if v_u_43 ~= v_u_9:invalid_loadout_index() then
                        l_LoadoutNameDisplay_0.Text = v_u_9:player_settings_get_loadout_name(p_u_23._player_settings_manager:get_player_settings(), p46)
                    end;
                end;
                return v45;
            end;
            v_u_33 = p_u_27:add_cycle_element(p_u_23, 1, v_u_5:new(v_u_4:new(p_u_27, p_u_26.PrimaryPart, p_u_26.Buttons.LoadoutDownArrow), p_u_24, function() --[[ Line: 111 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_7, (ref 3): v_u_41, (ref 4): v_u_28 ]]
                p_u_23._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                v_u_41:next_page()
                v_u_28:update_display()
            end))
            v_u_32 = p_u_27:add_cycle_element(p_u_23, 1, v_u_5:new(v_u_4:new(p_u_27, p_u_26.PrimaryPart, p_u_26.Buttons.LoadoutUpArrow), p_u_24, function() --[[ Line: 121 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_7, (ref 3): v_u_41, (ref 4): v_u_28 ]]
                p_u_23._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                v_u_41:prev_page()
                v_u_28:update_display()
            end))
            local l_LoadoutButtonSection_0 = p_u_26.LoadoutButtonSection
            local l_LoadoutButtonProto_0 = l_LoadoutButtonSection_0.LoadoutButtonProto
            l_LoadoutButtonProto_0.Parent = nil
            for _, v47 in v_u_3:new({
                l_LoadoutButtonSection_0.Anchors["1"],
                l_LoadoutButtonSection_0.Anchors["2"],
                l_LoadoutButtonSection_0.Anchors["3"],
                l_LoadoutButtonSection_0.Anchors["4"],
                l_LoadoutButtonSection_0.Anchors["5"]
            }):key_itr() do
                v47.Parent = nil
                local v48 = l_LoadoutButtonProto_0:Clone()
                v48.Parent = p_u_26
                v48:SetPrimaryPartCFrame(v47.PrimaryPart.CFrame)
                v_u_41:push_display_element((f_create_loadout_button(v48)))
            end;
            v_u_41:page_update()
            v_u_31 = p_u_27:add_cycle_element(p_u_23, 1, v_u_5:new(v_u_4:new(p_u_27, p_u_26.PrimaryPart, p_u_26.Buttons.IncreaseLoadoutsButton), p_u_24, function() --[[ Line: 149 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_7, (ref 3): p_u_27, (ref 4): v_u_9, (ref 5): p_u_25, (ref 6): v_u_14, (ref 7): p_u_24, (ref 8): v_u_15, (ref 9): v_u_17, (ref 10): v_u_18, (ref 11): v_u_16 ]]
                p_u_23._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                p_u_27:save_equip_changes(function() --[[ Line: 151 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_9, (ref 3): p_u_25, (ref 4): v_u_14, (ref 5): p_u_24, (ref 6): v_u_15, (ref 7): v_u_17, (ref 8): v_u_7, (ref 9): v_u_18, (ref 10): v_u_16 ]]
                    local v_u_49 = p_u_23._player_blob_manager:get_player_blob()
                    if v_u_9:can_playerblob_upgrade_loadout_slot_level(v_u_49) == true then
                        local v_u_50 = v_u_9:get_default_loadout_index_max() + v_u_9:playerblob_get_loadout_slot_level(v_u_49)
                        local v_u_51 = v_u_50 + 1
                        local v_u_52, v_u_53 = v_u_9:loadout_slot_level_to_price(v_u_9:playerblob_get_loadout_slot_level(v_u_49) + 1)
                        p_u_25:push_menu(v_u_14:new(p_u_23, p_u_24, p_u_25):set_text("Confirm", string.format("Do you want to increase your maximum number loadouts from %d to %d? This will cost %d %s. (You currently have %d %s)", v_u_50, v_u_51, v_u_52, v_u_15:currency_type_to_string(v_u_53), v_u_15:get_currency_type_amount(v_u_49, v_u_53), v_u_15:currency_type_to_string(v_u_53))):set_okay_button_fn(function() --[[ Line: 171 ]]
                            --[[ Upvalues: (ref 1): p_u_25, (ref 2): v_u_14, (ref 3): p_u_23, (ref 4): p_u_24, (ref 5): v_u_17, (ref 6): v_u_7, (copy 7): v_u_50, (copy 8): v_u_51, (ref 9): v_u_18, (ref 10): v_u_16, (copy 11): v_u_49, (copy 12): v_u_53, (copy 13): v_u_52 ]]
                            local function f_do_purchase() --[[ Name: do_purchase ]] --[[ Line: 172 ]]
                                --[[ Upvalues: (ref 1): p_u_25, (ref 2): v_u_14, (ref 3): p_u_23, (ref 4): p_u_24, (ref 5): v_u_17, (ref 6): v_u_7, (ref 7): v_u_50, (ref 8): v_u_51, (ref 9): v_u_18 ]]
                                local v_u_54 = p_u_25:push_menu(v_u_14:new(p_u_23, p_u_24, p_u_25):set_text("Loading...", ""):set_close_button_visible(false))
                                p_u_23._evt:wait_on_event_once(v_u_17.EVT_Lobby_ServerResponseIncreaseLoadoutLevel, function(p55, p56, p_u_57) --[[ Line: 174 ]]
                                    --[[ Upvalues: (ref 1): p_u_25, (copy 2): v_u_54, (ref 3): v_u_14, (ref 4): p_u_23, (ref 5): p_u_24, (ref 6): v_u_7, (ref 7): v_u_50, (ref 8): v_u_51, (ref 9): v_u_18 ]]
                                    if p55 == true then
                                        p_u_23._player_blob_manager:do_sync(function() --[[ Line: 180 ]]
                                            --[[ Upvalues: (ref 1): p_u_25, (ref 2): v_u_54, (ref 3): p_u_23, (ref 4): v_u_7, (ref 5): v_u_50, (ref 6): v_u_51, (ref 7): v_u_18, (copy 8): p_u_57, (ref 9): v_u_14, (ref 10): p_u_24 ]]
                                            p_u_25:remove_menu(v_u_54)
                                            p_u_23._sfx_manager:play_sfx(v_u_7.SFX_ACQUIRE)
                                            local v58 = string.format("Your maximum number of loadouts has been increased from %d to %d!", v_u_50, v_u_51)
                                            local v59 = v_u_18.RewardInfo:table_to_list(p_u_57)
                                            if v59:count() > 0 then
                                                v58 = v58 .. "\n" .. v_u_18:generate_description_from_rewardinfo_list(v59)
                                            end;
                                            p_u_25:push_menu(v_u_14:new(p_u_23, p_u_24, p_u_25):set_text("Success", v58))
                                        end)
                                    else
                                        p_u_25:remove_menu(v_u_54)
                                        p_u_25:push_menu(v_u_14:new(p_u_23, p_u_24, p_u_25):set_text("Failed", p56))
                                    end;
                                end)
                                p_u_23._evt:fire_event_to_server(v_u_17.EVT_Lobby_ClientRequestIncreaseLoadoutLevel)
                            end;
                            local v60 = v_u_16:playerblob_purchase_needs_redirect(v_u_49, v_u_53, v_u_52)
                            if v60:is_valid() then
                                v_u_16:show_purchase_redirect(p_u_23, v60, function(p61) --[[ Line: 202 ]]
                                    --[[ Upvalues: (copy 1): f_do_purchase ]]
                                    if p61 then
                                        f_do_purchase()
                                    end;
                                end)
                            else
                                f_do_purchase()
                            end;
                        end))
                    end;
                end)
            end)):set_auto_zoffset_behaviour(true)
            v_u_5:button_add_enabled_anim(v_u_31, function() --[[ Line: 216 ]]
                --[[ Upvalues: (ref 1): p_u_27 ]]
                return p_u_27:get_alpha();
            end)
            p_u_27:add_cycle_element(p_u_23, 1, v_u_5:new(v_u_4:new(p_u_27, p_u_26.PrimaryPart, p_u_26.Buttons.EditLoadoutNameButton), p_u_24, function() --[[ Line: 221 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_7, (ref 3): p_u_27, (ref 4): v_u_21, (ref 5): v_u_41, (ref 6): v_u_9, (ref 7): v_u_1, (ref 8): p_u_25, (ref 9): v_u_22, (ref 10): p_u_24, (ref 11): v_u_14, (ref 12): v_u_17, (ref 13): v_u_6, (ref 14): v_u_19 ]]
                p_u_23._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                p_u_27:save_equip_changes(function() --[[ Line: 223 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_21, (ref 3): v_u_41, (ref 4): v_u_9, (ref 5): v_u_1, (ref 6): p_u_25, (ref 7): v_u_22, (ref 8): p_u_24, (ref 9): v_u_14, (ref 10): v_u_17, (ref 11): v_u_6, (ref 12): v_u_19 ]]
                    p_u_23._menus:push_menu(v_u_21:new(p_u_23, p_u_23._spui, p_u_23._menus, function(p62) --[[ Line: 225 ]]
                        --[[ Upvalues: (ref 1): v_u_41 ]]
                        p62:set_header_text("Edit Loadout Name")
                        p62:get_element_list():push_back_from_list(v_u_41:get_data_list())
                    end, function(p63, p64, p65, _, p66) --[[ Line: 229 ]]
                        --[[ Upvalues: (ref 1): v_u_9, (ref 2): p_u_23, (ref 3): v_u_1 ]]
                        if typeof(p63) == "number" then
                            p64.Text = v_u_9:player_settings_get_loadout_name(p_u_23._player_settings_manager:get_player_settings(), p63)
                            p65.Image = v_u_1:important_assetid()
                            p66:get_description_display().Text = string.format("Loadout #%d", p63)
                            p66:set_select_button_text("Edit")
                        end;
                    end, function(p_u_67) --[[ Line: 237 ]]
                        --[[ Upvalues: (ref 1): p_u_25, (ref 2): v_u_22, (ref 3): p_u_23, (ref 4): p_u_24, (ref 5): v_u_9, (ref 6): v_u_14, (ref 7): v_u_17, (ref 8): v_u_1, (ref 9): v_u_6, (ref 10): v_u_19 ]]
                        if p_u_67 then
                            p_u_25:push_menu(v_u_22:new(p_u_23, p_u_24, p_u_25, string.format("Edit Name for Loadout #%d", p_u_67), string.format("Update this loadout\'s name (Max %d characters).\nYour name will be run through roblox moderation.", v_u_9:max_loadout_name_length()), function(p68) --[[ Line: 244 ]]
                                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_14, (ref 3): v_u_17, (ref 4): p_u_25, (ref 5): p_u_24, (ref 6): v_u_1, (ref 7): v_u_6, (ref 8): v_u_19, (copy 9): p_u_67 ]]
                                local v_u_69 = p_u_23._menus:push_menu(v_u_14:new(p_u_23, p_u_23._spui, p_u_23._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                                p_u_23._evt:wait_on_event_once(v_u_17.EVT_Lobby_ServerResponseLoadoutNameChanged, function(p_u_70, p_u_71) --[[ Line: 246 ]]
                                    --[[ Upvalues: (ref 1): p_u_23, (copy 2): v_u_69, (ref 3): p_u_25, (ref 4): v_u_14, (ref 5): p_u_24, (ref 6): v_u_1, (ref 7): v_u_6, (ref 8): v_u_19 ]]
                                    p_u_23._player_blob_manager:do_sync(function() --[[ Line: 247 ]]
                                        --[[ Upvalues: (copy 1): p_u_70, (ref 2): p_u_23, (ref 3): v_u_69, (ref 4): p_u_25, (ref 5): v_u_14, (ref 6): p_u_24, (copy 7): p_u_71, (ref 8): v_u_1, (ref 9): v_u_6, (ref 10): v_u_19 ]]
                                        if p_u_70 ~= true then
                                            p_u_23._menus:remove_menu(v_u_69)
                                            return p_u_25:push_menu(v_u_14:new(p_u_23, p_u_24, p_u_25):set_text("Failed", p_u_71));
                                        end;
                                        p_u_23._menus:remove_menu(v_u_69)
                                        if v_u_1:is_dev_build() then
                                            v_u_6:puts(v_u_1:table_to_string(p_u_23._player_settings_manager:get_key(v_u_19.Key.LoadoutNames)))
                                        end;
                                    end)
                                end)
                                p_u_23._evt:fire_event_to_server(v_u_17.EVT_Lobby_ClientRequestLoadoutNameChanged, p_u_67, p68)
                            end):set_empty_message(string.format("Loadout %d", p_u_67)):set_max_length(v_u_9:max_loadout_name_length()))
                        end;
                    end)):set_close_on_element_select(false):set_refresh_on_refocus(true)
                end)
            end))
        end;
        v_u_28.on_updated_loadout_index = function(p72) --[[ Name: on_updated_loadout_index ]] --[[ Line: 272 ]]
            --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_9, (copy 3): p_u_27 ]]
            if v_u_29 ~= v_u_9:invalid_loadout_index() then
                p_u_27:animate_equip_for_playerblob_change(function(p73) --[[ Line: 274 ]]
                    --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_29 ]]
                    v_u_9:equip_loadout_index(p73, v_u_29)
                end)
            end;
            p72:update_display()
        end;
        v_u_28.update_from_playerblob = function(_, p74) --[[ Name: update_from_playerblob ]] --[[ Line: 281 ]]
            --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_9, (ref 3): v_u_30 ]]
            if v_u_29 ~= v_u_9:invalid_loadout_index() then
                v_u_9:update_loadout_index_to_equipped(p74, v_u_29)
                v_u_30 = true
            end;
        end;
        v_u_28.update_display = function(_) --[[ Name: update_display ]] --[[ Line: 288 ]]
            --[[ Upvalues: (copy 1): v_u_41, (copy 2): p_u_23, (ref 3): v_u_9, (ref 4): v_u_29, (ref 5): v_u_10, (ref 6): v_u_11, (ref 7): v_u_31 ]]
            v_u_41:page_update()
            local v75 = p_u_23._player_blob_manager:get_player_blob()
            for _, v76 in v_u_41:get_display_elements():key_itr() do
                local v77 = v76:get_loadout_index()
                if v77 == v_u_9:invalid_loadout_index() then
                    v76.Button:set_visible(false)
                    v76.Toggle:set_toggle(false)
                else
                    v76.Button:set_visible(true)
                    v76.Toggle:set_toggle(v_u_29 == v77)
                end;
            end;
            local v78 = v_u_9:get_index_to_loadouts_multidict(v75)
            for _, v79 in v_u_41:get_display_elements():key_itr() do
                local v80 = v79:get_loadout_index()
                local v81 = v78:list_of(v80)
                local v82, v83, v84 = v_u_9:loadout_get_gear_power(v75, v80, p_u_23._player_blob_manager:get_dayid(), p_u_23._player_blob_manager:get_weekid())
                v_u_10:ranked_colors_statsdict_filter(v83, v84)
                v79.GearPowerDisplay.Text = tostring(v82)
                if v81:count() == 0 then
                    v79.PrimaryColorIcon.Visible = false
                    v79.SecondaryColorIcon.Visible = false
                else
                    v_u_11:render_color_section(v79.PrimaryColorIcon, v79.SecondaryColorIcon, v83)
                end;
            end;
            v_u_31:set_enabled(v_u_9:can_playerblob_upgrade_loadout_slot_level(v75))
        end;
        v_u_28.match_initial_selected_loadout = function(p85) --[[ Name: match_initial_selected_loadout ]] --[[ Line: 330 ]]
            --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_9, (copy 3): p_u_23, (ref 4): v_u_8, (ref 5): v_u_12, (ref 6): v_u_2, (copy 7): v_u_41 ]]
            v_u_29 = v_u_9:invalid_loadout_index()
            local v86 = p_u_23._player_blob_manager:get_player_blob()
            local v87 = v_u_8:get_equipped_ownedid_set(v86)
            local v88 = v_u_12:playerblob_get_slot_to_owned_pet_dict(v86)
            if v87:count() > 0 or v88:count() > 0 then
                local v89 = v_u_9:get_loadout_index_range(v86)
                for v90 = v89:min(), v89:max() do
                    if v_u_2:set_equals(v87, (v_u_9:get_index_ownedid_set(v86, v90))) == true and v_u_12:cmp_slot_to_ownedpet_dict(v88, (v_u_9:get_index_pet_slot_to_ownedpet_dict(v86, v90))) == true then
                        v_u_29 = v90
                        v_u_41:go_to_page(v_u_41:get_page_of_element(v_u_29))
                        p85:update_display()
                        return;
                    end;
                end;
            end;
        end;
        v_u_28.clear_loadout_change = function(_) --[[ Name: clear_loadout_change ]] --[[ Line: 351 ]]
            --[[ Upvalues: (ref 1): v_u_30 ]]
            v_u_30 = false
        end;
        f_cons()
        return v_u_28;
    end
};
