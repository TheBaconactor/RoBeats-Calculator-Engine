-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:47 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_9 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.LoginRewardUtil)
local v_u_11 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_12 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_13 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v14 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_15 = nil
local v_u_16 = nil
local v_u_17 = nil
v14:require_client(function() --[[ Line: 22 ]]
    --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_16, (ref 3): v_u_17 ]]
    v_u_15 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.CraftingMaterialsAcquiredUI)
    v_u_17 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
end)
return {
    ["new"] = function(_, p_u_18, p_u_19, p_u_20, p_u_21) --[[ Name: new ]] --[[ Line: 30 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_5, (copy 4): v_u_4, (copy 5): v_u_6, (copy 6): v_u_10, (ref 7): v_u_15, (copy 8): v_u_7, (copy 9): v_u_13, (ref 10): v_u_17, (copy 11): v_u_12, (ref 12): v_u_16, (copy 13): v_u_9, (copy 14): v_u_2, (copy 15): v_u_11, (copy 16): v_u_8 ]]
        local v_u_22 = v_u_3:new(p_u_19, p_u_20)
        local v_u_23 = nil
        local v_u_24 = nil
        local v_u_25 = nil
        local v_u_26 = nil
        local function f_cons() --[[ Name: cons ]] --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_1, (copy 3): v_u_22, (copy 4): p_u_18, (ref 5): v_u_5, (ref 6): v_u_4, (copy 7): p_u_19, (ref 8): v_u_6, (copy 9): p_u_20, (ref 10): v_u_10, (ref 11): v_u_15, (ref 12): v_u_7, (copy 13): p_u_21, (ref 14): v_u_13, (ref 15): v_u_17, (ref 16): v_u_12, (ref 17): v_u_16, (ref 18): v_u_24, (ref 19): v_u_9, (ref 20): v_u_2, (ref 21): v_u_11, (ref 22): v_u_25, (ref 23): v_u_26 ]]
            v_u_23 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.LoginRewardUI:Clone()
            v_u_23.Name = v_u_1:gen_name(v_u_23.Name)
            v_u_22:set_showing(true)
            v_u_22._native_size = v_u_23.PrimaryPart.Size
            v_u_22._size = v_u_22._native_size
            v_u_22:add_cycle_element(p_u_18, 1, v_u_5:new(v_u_4:new(v_u_22, v_u_23.PrimaryPart, v_u_23.BackButtonSurface), p_u_19, function() --[[ Line: 49 ]]
                --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_6, (ref 3): p_u_20, (ref 4): v_u_22 ]]
                p_u_18._sfx_manager:play_sfx(v_u_6.SFX_MENU_CLOSE)
                p_u_20:remove_menu(v_u_22)
            end))
            local v27 = p_u_18._player_blob_manager:get_player_blob()
            local v_u_28 = v_u_10:get_reward_day_count_for_playerblob_dayid_monthid(v27, p_u_18._player_blob_manager:get_dayid(), p_u_18._player_blob_manager:get_monthid())
            local v34 = v_u_22:add_cycle_element(p_u_18, 1, v_u_5:new(v_u_4:new(v_u_22, v_u_23.PrimaryPart, v_u_23.ClaimButton), p_u_19, function() --[[ Line: 65 ]]
                --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_6, (ref 3): p_u_20, (ref 4): v_u_15, (ref 5): p_u_19, (ref 6): v_u_7, (ref 7): p_u_21, (ref 8): v_u_22, (ref 9): v_u_13, (ref 10): v_u_17, (ref 11): v_u_12, (ref 12): v_u_16 ]]
                p_u_18._sfx_manager:play_sfx(v_u_6.SFX_MENU_OPEN)
                local v_u_29 = p_u_20:push_menu(v_u_15:new(p_u_18, p_u_19, p_u_20):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                p_u_18._evt:wait_on_event_once(v_u_7.EVT_PlayerBlob_ClaimLoginRewardServer, function(p30, p31, p_u_32, p_u_33) --[[ Line: 72 ]]
                    --[[ Upvalues: (ref 1): p_u_21, (ref 2): p_u_20, (ref 3): v_u_22, (ref 4): p_u_18, (copy 5): v_u_29, (ref 6): v_u_15, (ref 7): p_u_19, (ref 8): v_u_13, (ref 9): v_u_17, (ref 10): v_u_12, (ref 11): v_u_16 ]]
                    if p_u_21 then
                        p_u_21()
                    end;
                    p_u_20:remove_menu(v_u_22)
                    if p30 == true then
                        p_u_18._player_blob_manager:do_sync(function() --[[ Line: 81 ]]
                            --[[ Upvalues: (ref 1): p_u_20, (ref 2): v_u_29, (ref 3): v_u_13, (ref 4): v_u_17, (ref 5): p_u_18, (ref 6): p_u_19, (ref 7): v_u_12, (copy 8): p_u_32, (copy 9): p_u_33, (ref 10): v_u_16 ]]
                            p_u_20:remove_menu(v_u_29)
                            if v_u_13.UseRewardDescriptionInfoAcquiredUI == true then
                                p_u_20:push_menu(v_u_17:new(p_u_18, p_u_19, p_u_20, v_u_12.RewardInfo:table_to_list(p_u_32)):set_header_text("Daily Login Rewards Acquired!"):set_sub_text(string.format("For logging in %d day(s) this month, you have received...", p_u_33)))
                            else
                                p_u_20:push_menu(v_u_16:new(p_u_18, p_u_19, p_u_20, v_u_12.RewardInfo:table_to_list(p_u_32)))
                            end;
                        end)
                    else
                        p_u_18._menus:remove_menu(v_u_29)
                        p_u_20:push_menu(v_u_15:new(p_u_18, p_u_19, p_u_20):set_text("Failed", p31))
                    end;
                end)
                p_u_18._evt:fire_event_to_server(v_u_7.EVT_PlayerBlob_ClaimLoginRewardClient)
            end)):set_passive_anim(true)
            v_u_5:button_add_enabled_anim(v34, function() --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_22 ]]
                return v_u_22:get_alpha();
            end)
            v34:set_enabled(v_u_10:playerblob_can_claim_login_reward_for_dayid_monthid(v27, p_u_18._player_blob_manager:get_dayid(), p_u_18._player_blob_manager:get_monthid()))
            local l_ElementProto_0 = v_u_23.ElementProto
            l_ElementProto_0.Parent = nil
            local v_u_35 = l_ElementProto_0.PrimaryPart.SurfaceGui.ZOffset + 1000
            v_u_24 = v_u_9:new():set_fn_get_data_list(function() --[[ Line: 110 ]]
                --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_28 ]]
                return v_u_2:new():push_back_table_list({
                    v_u_28 - 2,
                    v_u_28 - 1,
                    v_u_28,
                    v_u_28 + 1,
                    v_u_28 + 2
                });
            end):set_fn_set_element_data(function(p36, p37) --[[ Line: 119 ]]
                --[[ Upvalues: (ref 1): v_u_10, (ref 2): p_u_18, (ref 3): v_u_11, (copy 4): v_u_28, (ref 5): v_u_1, (copy 6): v_u_35 ]]
                local v38 = v_u_10:get_reward_for_day_count(p37, p_u_18._player_blob_manager:get_monthid())
                local l_PrimaryPart_0 = p36:get_obj().PrimaryPart
                local l_SurfaceGui_0 = l_PrimaryPart_0.SurfaceGui
                if v38:count() == 0 then
                    l_SurfaceGui_0.Enabled = false
                    return;
                else
                    l_SurfaceGui_0.Enabled = true
                    local l_Frame_0 = l_PrimaryPart_0.SurfaceGui.Frame
                    l_Frame_0.DayDisplaySection.Display.Text = tostring(p37)
                    l_Frame_0.DayDisplaySection.Display.TextColor3 = v_u_11:singleton():get_difficulty_color_for_difficulty(p37)
                    local v39 = math.abs(p37 - v_u_28)
                    if p37 < v_u_28 then
                        l_Frame_0.Icon.Image = v_u_1:get_icon_box_open_assetid()
                        l_Frame_0.Shine.Visible = false
                        p36:get_uichild():set_scale(1 - v39 * 0.25)
                        l_SurfaceGui_0.ZOffset = v_u_35 - v39 * 100
                        p36:set_alpha(0.25)
                        return;
                    elseif p37 == v_u_28 then
                        l_Frame_0.Icon.Image = v_u_1:get_icon_box_closed_assetid()
                        l_Frame_0.Shine.Visible = true
                        p36:get_uichild():set_scale(1)
                        l_SurfaceGui_0.ZOffset = v_u_35
                        p36:set_alpha(1)
                    else
                        l_Frame_0.Icon.Image = v_u_1:get_icon_box_closed_assetid()
                        l_Frame_0.Shine.Visible = false
                        p36:get_uichild():set_scale(1 - v39 * 0.25)
                        l_SurfaceGui_0.ZOffset = v_u_35 - v39 * 100
                        p36:set_alpha(1)
                    end;
                end;
            end)
            for _, v40 in v_u_2:new():push_back_table_list({
                v_u_23.Anchors.Anchor1,
                v_u_23.Anchors.Anchor2,
                v_u_23.Anchors.Anchor3,
                v_u_23.Anchors.Anchor4,
                v_u_23.Anchors.Anchor5
            }):key_itr() do
                local v41 = l_ElementProto_0:Clone()
                v41:SetPrimaryPartCFrame(v40.PrimaryPart.CFrame)
                v41.Parent = v_u_23
                v_u_24:push_display_element(v_u_9.DisplayElement:new(v_u_22, v_u_23.PrimaryPart, v41):set_fn_get_parent_alpha(function() --[[ Line: 169 ]]
                    --[[ Upvalues: (ref 1): v_u_22 ]]
                    return v_u_22:get_alpha();
                end))
            end;
            v_u_24:page_update()
            local l_LoadedSection_0 = v_u_23.PrimaryPart.SurfaceGui.Frame.LoadedSection
            v_u_25 = l_LoadedSection_0.TimeToNextDayDisplay
            v_u_26 = l_LoadedSection_0.MonthDaysDisplay
            v_u_22:transition_update_visual(0)
            v_u_22:layout()
        end;
        v_u_22.behaviour_update = function(p42, p43, p44) --[[ Name: behaviour_update ]] --[[ Line: 184 ]]
            --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_1, (copy 3): p_u_18, (ref 4): v_u_26 ]]
            p42:behaviour_update_base(p43, p44)
            v_u_25.Text = v_u_1:format_sec_time(p_u_18._player_blob_manager:get_time_to_next_day_sec())
            v_u_26.Text = string.format("%d day(s)", math.floor(p_u_18._player_blob_manager:get_time_to_next_month_sec() / 86400) + 1)
        end;
        v_u_22.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 194 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            v_u_23:Destroy()
        end;
        local v_u_45 = 1
        local v_u_46 = 1
        v_u_22.layout = function(p47) --[[ Name: layout ]] --[[ Line: 200 ]]
            --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_46, (ref 3): v_u_23, (ref 4): v_u_24 ]]
            p47:opt_rescale_to_max_nxy(p_u_19, 0.8, 0.8, v_u_46)
            local v48, v49 = p47:opt_update_cframe_params(p_u_19, {
                ["PositionNXY"] = Vector2.new(0.5, 0.5),
                ["OffsetXYZ"] = p47:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            })
            if v48 == true then
                v_u_23:SetPrimaryPartCFrame(v49)
            end;
            v_u_24:layout()
        end;
        v_u_22.set_alpha = function(_, p50) --[[ Name: set_alpha ]] --[[ Line: 214 ]]
            --[[ Upvalues: (ref 1): v_u_45, (ref 2): v_u_1, (ref 3): v_u_23 ]]
            if v_u_45 ~= p50 then
                v_u_45 = p50
                v_u_1:r_set_alpha(v_u_23, v_u_45)
            end;
        end;
        v_u_22.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 220 ]]
            --[[ Upvalues: (ref 1): v_u_45 ]]
            return v_u_45;
        end;
        v_u_22.set_scale = function(_, p51) --[[ Name: set_scale ]] --[[ Line: 221 ]]
            --[[ Upvalues: (ref 1): v_u_46 ]]
            v_u_46 = p51
        end;
        v_u_22.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 222 ]]
            --[[ Upvalues: (ref 1): v_u_46 ]]
            return v_u_46;
        end;
        v_u_22.get_native_size = function(p52) --[[ Name: get_native_size ]] --[[ Line: 224 ]]
            return p52._native_size;
        end;
        v_u_22.get_size = function(p53) --[[ Name: get_size ]] --[[ Line: 227 ]]
            return p53._size;
        end;
        v_u_22.set_size = function(p54, p55) --[[ Name: set_size ]] --[[ Line: 230 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            p54._size = p55
            v_u_23.PrimaryPart.Size = Vector3.new(p55.X, p55.Y, 0)
        end;
        v_u_22.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 234 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            return v_u_23.PrimaryPart.Position;
        end;
        v_u_22.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 237 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            return v_u_23.PrimaryPart.SurfaceGui;
        end;
        v_u_22.set_showing = function(_, p56) --[[ Name: set_showing ]] --[[ Line: 240 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_8 ]]
            if p56 then
                v_u_23.Parent = v_u_8:get_world_ui_folder()
            else
                v_u_23.Parent = nil
            end;
        end;
        f_cons()
        return v_u_22;
    end
};
