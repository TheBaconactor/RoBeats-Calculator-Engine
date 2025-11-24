-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:46 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_2 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_5 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_6 = require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_9 = require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_10 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Lobby.UI.GearEquipV2UI.GearEquipV2GearStatDisplay)
require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_11 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
local v_u_12 = require(game.ReplicatedStorage.Lobby.UI.EquipUI.CharacterDisplaySection)
local v_u_13 = require(game.ReplicatedStorage.Lobby.UI.GearEquipV2UI.GearEquipV2GearStatDisplay)
local v_u_14 = require(game.ReplicatedStorage.Lobby.Menus.MaterialSelectUI)
local v_u_15 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_16 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_17 = require(game.ReplicatedStorage.Pets.PetInfoBase)
local v_u_18 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v_u_19 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_20 = require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_21 = require(game.ReplicatedStorage.Pets.PetUtils)
local v22 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_23 = nil
local v_u_24 = nil
v22:require_client(function() --[[ Line: 36 ]]
    --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_24 ]]
    v_u_23 = require(game.ReplicatedStorage.Lobby.Menus.RankUpPetUI)
    v_u_24 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
end)
return {
    ["new"] = function(_, p_u_25, p_u_26, p_u_27, p_u_28) --[[ Name: new ]] --[[ Line: 43 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_7, (copy 4): v_u_13, (copy 5): v_u_4, (copy 6): v_u_3, (copy 7): v_u_8, (copy 8): v_u_21, (copy 9): v_u_20, (copy 10): v_u_5, (copy 11): v_u_11, (copy 12): v_u_19, (copy 13): v_u_17, (ref 14): v_u_23, (copy 15): v_u_12, (ref 16): v_u_24, (copy 17): v_u_16, (copy 18): v_u_14, (copy 19): v_u_10, (copy 20): v_u_15, (copy 21): v_u_9 ]]
        local v29 = v_u_2:new(p_u_26, p_u_27)
        local v_u_30 = nil
        local v_u_31 = 1
        local v_u_32 = 1
        local v_u_33 = nil
        local v_u_34 = nil
        local v_u_35 = nil
        local v_u_36 = nil
        local v_u_37 = nil
        local v_u_38 = nil
        local v_u_39 = nil
        local v_u_40 = nil
        local v_u_41 = nil
        local function f_set_bar_num_div(p42, p43) --[[ Name: set_bar_num_div ]] --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_40, (ref 3): v_u_41 ]]
            local v44 = Vector2.new(437, 24)
            local v45 = Vector2.new(494, 31)
            local v46 = v_u_1:clamp(p42 / p43, 0, 1)
            v_u_40.Text = string.format("%s / %s", v_u_1:comma_value(p42), v_u_1:comma_value(p43))
            v_u_41.ImageRectSize = v44 * Vector2.new(v46, 1)
            v_u_41.Size = UDim2.new(0, v45.X * v46, 0, v45.Y)
        end;
        v29.cons = function(p_u_47) --[[ Name: cons ]] --[[ Line: 69 ]]
            --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_1, (ref 3): v_u_7, (ref 4): v_u_33, (ref 5): v_u_41, (ref 6): v_u_40, (ref 7): v_u_35, (ref 8): v_u_13, (copy 9): p_u_25, (ref 10): v_u_4, (ref 11): v_u_3, (copy 12): p_u_26, (ref 13): v_u_8, (copy 14): p_u_27, (ref 15): v_u_36, (ref 16): v_u_21, (copy 17): p_u_28, (ref 18): v_u_20, (ref 19): v_u_5, (ref 20): v_u_11, (ref 21): v_u_37, (ref 22): v_u_19, (ref 23): v_u_17, (ref 24): v_u_38, (ref 25): v_u_39, (ref 26): v_u_23, (ref 27): v_u_34, (ref 28): v_u_12 ]]
            v_u_30 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Pets.TrainPetUI:Clone()
            v_u_30.Name = v_u_1:gen_name(v_u_30.Name)
            v_u_30.Parent = v_u_7:get_world_ui_folder()
            p_u_47._native_size = v_u_30.PrimaryPart.Size
            p_u_47._size = p_u_47._native_size
            v_u_33 = v_u_30.MainSurface.SurfaceGui.Frame
            v_u_41 = v_u_33.ExpBarSection.BarFillYellow
            v_u_40 = v_u_33.ExpBarSection.ExpDisplay
            v_u_35 = v_u_13:new(nil, v_u_33.StatSection)
            p_u_47:add_cycle_element(p_u_25, 1, v_u_4:new(v_u_3:new(p_u_47, v_u_30.PrimaryPart, v_u_30.BackButtonSurface), p_u_26, function() --[[ Line: 84 ]]
                --[[ Upvalues: (ref 1): p_u_25, (ref 2): v_u_8, (ref 3): p_u_27, (copy 4): p_u_47 ]]
                p_u_25._sfx_manager:play_sfx(v_u_8.SFX_MENU_CLOSE)
                p_u_27:remove_menu(p_u_47)
            end))
            v_u_36 = p_u_47:add_cycle_element(p_u_25, 1, v_u_4:new(v_u_3:new(p_u_47, v_u_30.PrimaryPart, v_u_30.DeletePetButton), p_u_26, function() --[[ Line: 93 ]]
                --[[ Upvalues: (ref 1): p_u_25, (ref 2): v_u_8, (ref 3): v_u_21, (ref 4): p_u_28, (ref 5): v_u_20, (ref 6): p_u_27, (ref 7): v_u_5, (ref 8): p_u_26, (ref 9): v_u_11, (copy 10): p_u_47 ]]
                p_u_25._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
                local v48 = v_u_21:playerblob_get_pet_ownedid_ownedpet(p_u_25._player_blob_manager:get_player_blob(), p_u_28)
                if v48 == nil then
                    return;
                else
                    local v49 = v_u_20:singleton():get_data_for_petid((v_u_21:ownedpet_get_petid(v48)))
                    if v49 ~= nil then
                        p_u_27:push_menu(v_u_5:new(p_u_25, p_u_26, p_u_27):set_text("Confirm", string.format("Are you sure you want to delete \'%s\' Mini?", v49:get_name())):set_okay_button_fn(function() --[[ Line: 109 ]]
                            --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_5, (ref 3): p_u_25, (ref 4): p_u_26, (ref 5): v_u_11, (ref 6): p_u_47, (ref 7): v_u_8, (ref 8): p_u_28 ]]
                            local v_u_50 = p_u_27:push_menu(v_u_5:new(p_u_25, p_u_26, p_u_27):set_text("Loading...", ""):set_close_button_visible(false))
                            p_u_25._evt:wait_on_event_once(v_u_11.EVT_Pet_DeleteServerResponse, function(p51, p52) --[[ Line: 111 ]]
                                --[[ Upvalues: (ref 1): p_u_27, (copy 2): v_u_50, (ref 3): v_u_5, (ref 4): p_u_25, (ref 5): p_u_26, (ref 6): p_u_47, (ref 7): v_u_8 ]]
                                if p51 == true then
                                    p_u_25._player_blob_manager:do_sync(function() --[[ Line: 117 ]]
                                        --[[ Upvalues: (ref 1): p_u_27, (ref 2): p_u_47, (ref 3): v_u_50, (ref 4): p_u_25, (ref 5): v_u_8 ]]
                                        p_u_27:remove_menu(p_u_47)
                                        p_u_27:remove_menu(v_u_50)
                                        p_u_25._sfx_manager:play_sfx(v_u_8.SFX_ACQUIRE)
                                    end)
                                else
                                    p_u_27:remove_menu(v_u_50)
                                    p_u_27:push_menu(v_u_5:new(p_u_25, p_u_26, p_u_27):set_text("Failed", p52))
                                end;
                            end)
                            p_u_25._evt:fire_event_to_server(v_u_11.EVT_Pet_DeleteClientRequest, p_u_28)
                        end))
                    end;
                end;
            end))
            v_u_37 = p_u_47:add_cycle_element(p_u_25, 1, v_u_4:new(v_u_3:new(p_u_47, v_u_30.PrimaryPart, v_u_30.InfoButton), p_u_26, function() --[[ Line: 132 ]]
                --[[ Upvalues: (ref 1): p_u_25, (ref 2): v_u_8, (ref 3): v_u_21, (ref 4): p_u_28, (ref 5): v_u_19, (ref 6): v_u_17, (ref 7): p_u_27, (ref 8): v_u_5, (ref 9): p_u_26 ]]
                p_u_25._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                local v53 = v_u_21:playerblob_get_pet_ownedid_ownedpet(p_u_25._player_blob_manager:get_player_blob(), p_u_28)
                if v53 == nil then
                    return false;
                end;
                v_u_21:ownedpet_get_petid(v53)
                local v54 = "Train and level up this Mini to increase its stats. Color Elemental stats increase every level, and Base stats increase every rank. Level this mini to max level to be able to increase its rank. Mini EXP can be earned with the following:\n"
                if v_u_19.PetRankUpEnabled == true then
                    v54 = v54 .. string.format("Train with Gem - %d EXP\n", v_u_21:get_gem_train_amount())
                end;
                p_u_27:push_menu(v_u_5:new(p_u_25, p_u_26, p_u_27):set_text("Train Minis", ((((v54 .. string.format("Train with Large Note - %d EXP\n", v_u_21:get_large_note_train_amount())) .. string.format("Train with Medium Note - %d EXP\n", v_u_21:get_medium_note_train_amount())) .. string.format("Train with Small Note - %d EXP\n", v_u_21:get_small_note_train_amount())) .. string.format("Train with Mini - %d-%d EXP (Based on rarity and type)\n", v_u_21:sealed_mini_train_amount(v_u_17.Rarity.Tier1, false), v_u_21:sealed_mini_train_amount(v_u_17.Rarity.Tier2, true))) .. string.format("Play Match: %d-%d EXP (Based on performance, song and # of players)\n", v_u_21:get_play_exp_per_minute() * 1, v_u_21:get_play_exp_per_minute() * 6 * 4)))
            end))
            v_u_38 = p_u_47:add_cycle_element(p_u_25, 1, v_u_4:new(v_u_3:new(p_u_47, v_u_30.PrimaryPart, v_u_30.TrainButton), p_u_26, function() --[[ Line: 171 ]]
                --[[ Upvalues: (ref 1): p_u_25, (ref 2): v_u_8, (copy 3): p_u_47 ]]
                p_u_25._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
                p_u_47:on_train_button_pressed()
            end))
            v_u_4:button_add_enabled_anim(v_u_38, function() --[[ Line: 176 ]]
                --[[ Upvalues: (copy 1): p_u_47 ]]
                return p_u_47:get_alpha();
            end)
            v_u_38:set_enabled(true)
            v_u_39 = p_u_47:add_cycle_element(p_u_25, 1, v_u_4:new(v_u_3:new(p_u_47, v_u_30.PrimaryPart, v_u_30.RankUpButton), p_u_26, function() --[[ Line: 184 ]]
                --[[ Upvalues: (ref 1): p_u_25, (ref 2): v_u_8, (ref 3): p_u_27, (ref 4): v_u_23, (ref 5): p_u_26, (ref 6): p_u_28 ]]
                p_u_25._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
                p_u_27:push_menu(v_u_23:new(p_u_25, p_u_26, p_u_27, p_u_28))
            end)):set_auto_zoffset_behaviour(true)
            v_u_4:button_add_enabled_anim(v_u_39, function() --[[ Line: 189 ]]
                --[[ Upvalues: (copy 1): p_u_47 ]]
                return p_u_47:get_alpha();
            end)
            v_u_39:set_enabled(false)
            v_u_34 = v_u_12:new(p_u_25, p_u_26, v_u_3:new(p_u_47, v_u_30.PrimaryPart, v_u_30.RenderCharacterSurface), v_u_30.RenderCharacterSurface.SurfaceGui)
            p_u_47:update_display_from_playerblob()
        end;
        v29.update_display_from_playerblob = function(_) --[[ Name: update_display_from_playerblob ]] --[[ Line: 203 ]]
            --[[ Upvalues: (copy 1): p_u_25, (ref 2): v_u_21, (copy 3): p_u_28, (ref 4): v_u_20, (ref 5): v_u_34, (ref 6): v_u_33, (ref 7): v_u_35, (copy 8): f_set_bar_num_div, (ref 9): v_u_38, (ref 10): v_u_19, (ref 11): v_u_39 ]]
            local v55 = p_u_25._player_blob_manager:get_player_blob()
            local v56 = v_u_21:playerblob_get_pet_ownedid_ownedpet(v55, p_u_28)
            if v56 == nil then
                return false;
            else
                local v57 = v_u_20:singleton():get_data_for_petid((v_u_21:ownedpet_get_petid(v56)))
                v_u_34:set_character_visible(false)
                v57:create_character(v_u_20.DEFAULT_CREATE_PET_PARAMS, v_u_34:get_character_parent(), function(p58) --[[ Line: 211 ]]
                    --[[ Upvalues: (ref 1): v_u_34 ]]
                    v_u_34:replace_character_model(p58)
                    v_u_34:set_camera_radius(2.5)
                    v_u_34:set_dance_active(true)
                    v_u_34:play_selected_animation()
                end)
                v_u_33.NameSection.NameDisplay.Text = v57:get_name()
                v_u_33.NameSection.DescriptionDisplay.Text = v57:get_description()
                v_u_33.IconSection.Icon.Image = v57:get_icon()
                local v59 = v_u_21:ownedpet_get_level(v56)
                local v60 = v_u_21:ownedpet_get_max_level(v56)
                v_u_33.LevelSection.LevelDisplay.Text = string.format("%d / %d", v59, v60)
                v_u_33.LevelSection.RankDisplay.Text = string.format("%d", v_u_21:ownedpet_get_rank(v56))
                v_u_33.RaritySection.Icon.Image = v_u_21:pet_rarity_to_icon(v57:get_rarity())
                v_u_35:set_pet_ownedid(v55, p_u_28)
                if v59 < v60 then
                    f_set_bar_num_div(v_u_21:ownedpet_get_exp(v56) - v_u_21:get_exp_to_level(v59, v_u_21:ownedpet_get_rarity(v56)), (v_u_21:get_exp_for_next_level(v59, v_u_21:ownedpet_get_rarity(v56))))
                else
                    local v61 = v_u_21:get_exp_for_next_level(v59 - 1, v_u_21:ownedpet_get_rarity(v56))
                    f_set_bar_num_div(v61, v61)
                end;
                v_u_38:set_enabled(v59 < v60)
                if v_u_19.PetRankUpEnabled == true then
                    v_u_39:set_enabled(v_u_21:ownedpet_can_rank_up(v56))
                else
                    v_u_39:set_enabled(false)
                end;
            end;
        end;
        v29.on_train_button_pressed = function(_) --[[ Name: on_train_button_pressed ]] --[[ Line: 247 ]]
            --[[ Upvalues: (copy 1): p_u_25, (ref 2): v_u_21, (copy 3): p_u_28, (ref 4): v_u_24, (ref 5): v_u_16, (copy 6): p_u_27, (ref 7): v_u_5, (copy 8): p_u_26, (ref 9): v_u_14, (ref 10): v_u_10, (ref 11): v_u_15, (ref 12): v_u_19, (ref 13): v_u_11, (ref 14): v_u_8 ]]
            local v62 = p_u_25._player_blob_manager:get_player_blob()
            local v_u_63 = v_u_21:playerblob_get_pet_ownedid_ownedpet(v62, p_u_28)
            local v_u_64 = v_u_21:get_materialid_to_value_dict_of_train_consumable_materials_for_pet_id(v_u_21:ownedpet_get_petid(v_u_63), v_u_24:playerblob_has_vip_for_current_day(v62, p_u_25._player_blob_manager:get_day_id()))
            local v65 = v_u_16:get_owned_crafting_materials(v62)
            local v66 = false
            for v67, _ in v_u_64:key_itr() do
                if v65:contains(v67) then
                    v66 = true
                end;
            end;
            if v66 ~= true then
                return p_u_27:push_menu(v_u_5:new(p_u_25, p_u_26, p_u_27):set_text("No available materials.", "You can train this Mini with the following materials: Large/Medium/Small Notes (of Mini color), Minis (bonus EXP for same type)."));
            end;
            p_u_27:push_menu(v_u_14:new(p_u_25, p_u_26, p_u_27, function(p_u_68, p_u_69) --[[ Line: 275 ]]
                --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_15, (ref 3): v_u_21, (copy 4): v_u_63, (copy 5): v_u_64, (ref 6): v_u_19, (ref 7): p_u_27, (ref 8): v_u_5, (ref 9): p_u_25, (ref 10): p_u_26, (ref 11): v_u_11, (ref 12): v_u_8, (ref 13): p_u_28 ]]
                v_u_10:is_true(v_u_15:singleton():contains_material(p_u_68))
                v_u_10:is_int_greater_than(p_u_69, 1)
                local v70 = v_u_21:ownedpet_get_info_for_apply_exp_gain(v_u_63, v_u_64:get(p_u_68) * p_u_69)
                local v71 = string.format("Are you sure you want to use %s x%d to train this Mini? This will give %d EXP.", v_u_15:singleton():get_material_name(p_u_68), p_u_69, v70.GainedEXP)
                if v_u_19.PetRankUpEnabled == true and v_u_15:singleton():get_material(p_u_68):is_pet() then
                    v71 = v71 .. " (Minis can also be used for the rank up process)"
                end;
                if v70.WastedEXP > 0 then
                    v71 = v71 .. string.format(" (Wasted EXP: %d)", v70.WastedEXP)
                end;
                p_u_27:push_menu(v_u_5:new(p_u_25, p_u_26, p_u_27):set_text("Confirm", v71):set_okay_button_fn(function() --[[ Line: 300 ]]
                    --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_5, (ref 3): p_u_25, (ref 4): p_u_26, (ref 5): v_u_11, (ref 6): v_u_8, (ref 7): p_u_28, (copy 8): p_u_68, (copy 9): p_u_69 ]]
                    local v_u_72 = p_u_27:push_menu(v_u_5:new(p_u_25, p_u_26, p_u_27):set_text("Training...", ""):set_close_button_visible(false))
                    p_u_25._evt:wait_on_event_once(v_u_11.EVT_Pet_TrainPetServerResponse, function(p73, p74) --[[ Line: 302 ]]
                        --[[ Upvalues: (ref 1): p_u_27, (copy 2): v_u_72, (ref 3): v_u_5, (ref 4): p_u_25, (ref 5): p_u_26, (ref 6): v_u_8 ]]
                        if p73 == true then
                            p_u_25._player_blob_manager:do_sync(function(_) --[[ Line: 308 ]]
                                --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_72, (ref 3): p_u_25, (ref 4): v_u_8 ]]
                                p_u_27:remove_menu(v_u_72)
                                p_u_25._sfx_manager:play_sfx(v_u_8.SFX_ACQUIRE)
                            end)
                        else
                            p_u_27:remove_menu(v_u_72)
                            p_u_27:push_menu(v_u_5:new(p_u_25, p_u_26, p_u_27):set_text("Failed", p74))
                        end;
                    end)
                    p_u_25._evt:fire_event_to_server(v_u_11.EVT_Pet_TrainPetClientRequest, p_u_28, p_u_68, p_u_69)
                end))
            end):set_fn_material_ids_filter(function(p75) --[[ Line: 322 ]]
                --[[ Upvalues: (copy 1): v_u_64 ]]
                return v_u_64:contains(p75) ~= true;
            end))
        end;
        v29.layout = function(p76) --[[ Name: layout ]] --[[ Line: 328 ]]
            --[[ Upvalues: (copy 1): p_u_26, (ref 2): v_u_32, (ref 3): v_u_30, (ref 4): v_u_34 ]]
            p76:opt_rescale_to_max_nxy(p_u_26, 0.8, 0.8, v_u_32)
            local v77, v78 = p76:opt_update_cframe_params(p_u_26, {
                ["PositionNXY"] = Vector2.new(0.5, 0.5),
                ["OffsetXYZ"] = p76:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            })
            if v77 == true then
                v_u_30:SetPrimaryPartCFrame(v78)
            end;
            v_u_34:layout()
        end;
        v29.visual_update = function(p79, p80, p81) --[[ Name: visual_update ]] --[[ Line: 342 ]]
            --[[ Upvalues: (ref 1): v_u_35 ]]
            p79:visual_update_base(p80, p81)
            v_u_35:visual_update(p80)
        end;
        v29.behaviour_update = function(p82, p83, _) --[[ Name: behaviour_update ]] --[[ Line: 347 ]]
            --[[ Upvalues: (copy 1): p_u_25, (ref 2): v_u_9, (ref 3): v_u_34 ]]
            p82:behaviour_update_base(p83, p_u_25)
            if p82._current_mode == v_u_9.MODE_OPEN then
                v_u_34:behaviour_update(p83)
            end;
        end;
        v29.on_refocus = function(p84) --[[ Name: on_refocus ]] --[[ Line: 354 ]]
            p84:update_display_from_playerblob()
        end;
        v29.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 358 ]]
            --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_34 ]]
            v_u_30:Destroy()
            v_u_34:teardown()
        end;
        v29.set_alpha = function(_, p85) --[[ Name: set_alpha ]] --[[ Line: 363 ]]
            --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_1, (ref 3): v_u_30, (ref 4): v_u_34 ]]
            if v_u_31 ~= p85 then
                v_u_31 = p85
                v_u_1:r_set_alpha(v_u_30, v_u_31)
                v_u_34:set_alpha(v_u_31)
            end;
        end;
        v29.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 370 ]]
            --[[ Upvalues: (ref 1): v_u_31 ]]
            return v_u_31;
        end;
        v29.set_scale = function(_, p86) --[[ Name: set_scale ]] --[[ Line: 371 ]]
            --[[ Upvalues: (ref 1): v_u_32 ]]
            v_u_32 = p86
        end;
        v29.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 372 ]]
            --[[ Upvalues: (ref 1): v_u_32 ]]
            return v_u_32;
        end;
        v29.get_native_size = function(p87) --[[ Name: get_native_size ]] --[[ Line: 374 ]]
            return p87._native_size;
        end;
        v29.get_size = function(p88) --[[ Name: get_size ]] --[[ Line: 377 ]]
            return p88._size;
        end;
        v29.set_size = function(p89, p90) --[[ Name: set_size ]] --[[ Line: 380 ]]
            --[[ Upvalues: (ref 1): v_u_30 ]]
            p89._size = p90
            v_u_30.PrimaryPart.Size = Vector3.new(p90.X, p90.Y, 0)
        end;
        v29.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 384 ]]
            --[[ Upvalues: (ref 1): v_u_30 ]]
            return v_u_30.PrimaryPart.Position;
        end;
        v29.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 387 ]]
            --[[ Upvalues: (ref 1): v_u_30 ]]
            return v_u_30.PrimaryPart.SurfaceGui;
        end;
        v29.set_showing = function(_, p91) --[[ Name: set_showing ]] --[[ Line: 390 ]]
            --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_7 ]]
            if p91 then
                v_u_30.Parent = v_u_7:get_world_ui_folder()
            else
                v_u_30.Parent = nil
            end;
        end;
        v29:cons()
        return v29;
    end,
    ["use_pet_materialid"] = function(_, p_u_92, p_u_93) --[[ Name: use_pet_materialid ]] --[[ Line: 401 ]]
        --[[ Upvalues: (copy 1): v_u_15, (copy 2): v_u_6, (copy 3): v_u_18, (copy 4): v_u_21, (copy 5): v_u_5, (copy 6): v_u_11, (copy 7): v_u_8 ]]
        if v_u_15:singleton():contains_material(p_u_93) ~= true then
            return v_u_6:warnf("TrainPetUI:use_pet_materialid(%s) not found", (tostring(p_u_93)));
        end;
        if v_u_15:singleton():get_material_type(p_u_93) ~= v_u_18.Type.Pet then
            return v_u_6:warnf("TrainPetUI:use_pet_materialid(%d) not type pet", p_u_93);
        end;
        local l__spui_0 = p_u_92._spui
        local l__menus_0 = p_u_92._menus
        local v94, v95 = v_u_21:playerblob_can_add_pet_of_petid(p_u_92._player_blob_manager:get_player_blob(), (v_u_15:singleton():get_material(p_u_93):get_pet_id()))
        if v94 ~= true then
            return l__menus_0:push_menu(v_u_5:new(p_u_92, l__spui_0, l__menus_0):set_text("Cannot add Mini", v95));
        end;
        l__menus_0:push_menu(v_u_5:new(p_u_92, l__spui_0, l__menus_0):set_text("Confirm", string.format("Are you sure you want to claim this \'%s\'?", v_u_15:singleton():get_material_name(p_u_93))):set_okay_button_fn(function() --[[ Line: 422 ]]
            --[[ Upvalues: (copy 1): l__menus_0, (ref 2): v_u_5, (copy 3): p_u_92, (copy 4): l__spui_0, (ref 5): v_u_11, (ref 6): v_u_8, (ref 7): v_u_15, (copy 8): p_u_93 ]]
            local v_u_96 = l__menus_0:push_menu(v_u_5:new(p_u_92, l__spui_0, l__menus_0):set_text("Claiming...", ""):set_close_button_visible(false))
            p_u_92._evt:wait_on_event_once(v_u_11.EVT_Pet_ClaimPetFromMaterialServerResponse, function(p97, p98) --[[ Line: 424 ]]
                --[[ Upvalues: (ref 1): l__menus_0, (copy 2): v_u_96, (ref 3): v_u_5, (ref 4): p_u_92, (ref 5): l__spui_0, (ref 6): v_u_8, (ref 7): v_u_15, (ref 8): p_u_93 ]]
                if p97 == true then
                    p_u_92._player_blob_manager:do_sync(function(_) --[[ Line: 430 ]]
                        --[[ Upvalues: (ref 1): p_u_92, (ref 2): v_u_8, (ref 3): l__menus_0, (ref 4): v_u_96, (ref 5): v_u_5, (ref 6): l__spui_0, (ref 7): v_u_15, (ref 8): p_u_93 ]]
                        p_u_92._sfx_manager:play_sfx(v_u_8.SFX_ACQUIRE)
                        l__menus_0:remove_menu(v_u_96)
                        l__menus_0:push_menu(v_u_5:new(p_u_92, l__spui_0, l__menus_0):set_text("Claimed", string.format("Claimed %s!", v_u_15:singleton():get_material_name(p_u_93))))
                    end)
                else
                    l__menus_0:remove_menu(v_u_96)
                    l__menus_0:push_menu(v_u_5:new(p_u_92, l__spui_0, l__menus_0):set_text("Failed", p98))
                end;
            end)
            p_u_92._evt:fire_event_to_server(v_u_11.EVT_Pet_ClaimPetFromMaterialClientRequest, p_u_93)
        end))
    end
};
