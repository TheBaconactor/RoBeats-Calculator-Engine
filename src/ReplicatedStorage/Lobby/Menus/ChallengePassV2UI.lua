-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:48 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_2 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Lobby.Menus.VIPPurchaseUI)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.PurchaseUtils)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_7 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_8 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Data)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Mission)
local v11 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
local v_u_15 = nil
v11:require_client(function() --[[ Line: 30 ]]
    --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_13, (ref 3): v_u_14, (ref 4): v_u_15 ]]
    v_u_12 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_13 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
    v_u_14 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_15 = require(game.ReplicatedStorage.Lobby.Menus.VIPPurchaseUI)
end)
local v_u_62 = {
    ["show_daily_missions_menu"] = function(_, p16) --[[ Name: show_daily_missions_menu ]] --[[ Line: 42 ]]
        --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_10, (copy 3): v_u_1 ]]
        local v_u_17 = p16._player_blob_manager:get_player_blob()
        p16._menus:push_menu(v_u_12:new(p16, p16._spui, p16._menus, function(p18) --[[ Line: 48 ]]
            --[[ Upvalues: (ref 1): v_u_10, (copy 2): v_u_17 ]]
            p18:set_header_text("Daily Tasks")
            for v19, _ in v_u_10:get_daily_mission_type_set():key_itr() do
                if v_u_10:playerblob_daily_mission_flag_set(v_u_17, v19) ~= true then
                    p18:get_element_list():push_back(v19)
                end;
            end;
        end, function(p20, p21, p22, _, p23) --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_1 ]]
            p21.Text = v_u_10:get_daily_mission_name(p20)
            p22.Image = v_u_1:important_assetid()
            p23:set_select_button_enabled(false)
            p23:get_description_display().Text = string.format("%d Points", v_u_10:get_daily_mission_point_amount(p20))
        end, function(_) end, function(p24) --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_10, (copy 3): v_u_17 ]]
            p24:set_sub_text(string.format("Today: %s / %s Points", v_u_1:comma_value(v_u_10:playerblob_get_daily_mission_points(v_u_17)), v_u_1:comma_value(v_u_10:get_daily_point_cap())))
        end)):set_close_on_element_select(false)
    end,
    ["show_weekly_missions_menu"] = function(_, p25) --[[ Name: show_weekly_missions_menu ]] --[[ Line: 77 ]]
        --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_10, (copy 3): v_u_1 ]]
        local v_u_26 = p25._player_blob_manager:get_player_blob()
        p25._menus:push_menu(v_u_12:new(p25, p25._spui, p25._menus, function(p27) --[[ Line: 83 ]]
            --[[ Upvalues: (ref 1): v_u_10, (copy 2): v_u_26 ]]
            p27:set_header_text("Weekly Tasks")
            for v28, _ in v_u_10:get_weekly_mission_type_set():key_itr() do
                if v_u_10:playerblob_weekly_mission_flag_set(v_u_26, v28) ~= true then
                    p27:get_element_list():push_back(v28)
                end;
            end;
        end, function(p29, p30, p31, _, p32) --[[ Line: 91 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_1 ]]
            p30.Text = v_u_10:get_weekly_mission_name(p29)
            p31.Image = v_u_1:important_assetid()
            p32:set_select_button_enabled(false)
            p32:get_description_display().Text = string.format("%d Points", v_u_10:get_weekly_mission_point_amount(p29))
        end, function(_) end, function(p33) --[[ Line: 99 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_10, (copy 3): v_u_26 ]]
            p33:set_sub_text(string.format("This Week: %s / %s Points", v_u_1:comma_value(v_u_10:playerblob_get_weekly_mission_points(v_u_26)), v_u_1:comma_value(v_u_10:get_weekly_point_cap())))
        end)):set_close_on_element_select(false)
    end,
    ["show_challengepass_entry_rewards_menu"] = function(_, p_u_34, p_u_35, p_u_36) --[[ Name: show_challengepass_entry_rewards_menu ]] --[[ Line: 112 ]]
        --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_10, (ref 3): v_u_13 ]]
        local function _(p37) --[[ Name: claimed_bool_to_str ]] --[[ Line: 116 ]]
            return p37 and "Claimed" or "Not Claimed";
        end;
        p_u_34._menus:push_menu(v_u_12:new(p_u_34, p_u_34._spui, p_u_34._menus, function(p38) --[[ Line: 128 ]]
            --[[ Upvalues: (copy 1): p_u_36, (copy 2): p_u_34, (ref 3): v_u_10, (copy 4): p_u_35 ]]
            p38:set_header_text(string.format("Level %d Rewards", p_u_36))
            local v39 = p_u_34._player_blob_manager:get_player_blob()
            p38:set_sub_text(string.format("Free Tier: %s, VIP Tier: %s", p_u_36 <= v_u_10:playerblob_get_standard_claimed_tier(v39) and "Claimed" or "Not Claimed", p_u_36 <= v_u_10:playerblob_get_vip_claimed_tier(v39) and "Claimed" or "Not Claimed"))
            if p_u_35:get_reward_list_standard():count() > 0 then
                p38:get_element_list():push_back(-1)
            end;
            if p_u_35:get_reward_list_vip():count() > 0 then
                p38:get_element_list():push_back(-2)
            end;
        end, function(p40, p41, p42, _, p43, _, _) --[[ Line: 144 ]]
            --[[ Upvalues: (copy 1): p_u_35 ]]
            p43:set_select_button_text("View")
            if p40 == -1 then
                p41.Text = "Free Tier Rewards"
                p42.Image = p_u_35:get_icon(false)
                local v44 = p_u_35:get_amount(false)
                local v45 = p_u_35:get_name(false)
                if v44 > 0 then
                    p43:get_description_display().Text = string.format("x%d %s", v44, v45)
                else
                    p43:get_description_display().Text = ""
                end;
            else
                if p40 == -2 then
                    p41.Text = "VIP Tier Rewards"
                    p42.Image = p_u_35:get_icon(true)
                    local v46 = p_u_35:get_amount(true)
                    local v47 = p_u_35:get_name(true)
                    if v46 > 0 then
                        p43:get_description_display().Text = string.format("x%d %s", v46, v47)
                        return;
                    end;
                    p43:get_description_display().Text = ""
                end;
                return;
            end;
        end, function(p48) --[[ Line: 171 ]]
            --[[ Upvalues: (copy 1): p_u_34, (ref 2): v_u_13, (copy 3): p_u_35 ]]
            if p48 == nil then
                return;
            elseif p48 == -1 then
                p_u_34._menus:push_menu(v_u_13:new(p_u_34, p_u_34._spui, p_u_34._menus, p_u_35:get_reward_list_standard()):set_header_text("Free Tier Reward Preview"):set_sub_text(""):show_description_extra_text(false):finish_animation():select_first_element())
            elseif p48 == -2 then
                p_u_34._menus:push_menu(v_u_13:new(p_u_34, p_u_34._spui, p_u_34._menus, p_u_35:get_reward_list_vip()):set_header_text("VIP Tier Reward Preview"):set_sub_text(""):show_description_extra_text(false):finish_animation():select_first_element())
            end;
        end)):set_close_on_element_select(false)
    end,
    ["claim_challengepass_rewards"] = function(_, p_u_49) --[[ Name: claim_challengepass_rewards ]] --[[ Line: 259 ]]
        --[[ Upvalues: (ref 1): v_u_14, (copy 2): v_u_3, (ref 3): v_u_13, (copy 4): v_u_7 ]]
        local v_u_50 = p_u_49._menus:push_menu(v_u_14:new(p_u_49, p_u_49._spui, p_u_49._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
        p_u_49._evt:wait_on_event_once(v_u_3.EVT_ChallengePassV2_ServerClaimRewardsResponse, function(p_u_51) --[[ Line: 261 ]]
            --[[ Upvalues: (copy 1): p_u_49, (copy 2): v_u_50, (ref 3): v_u_13, (ref 4): v_u_7 ]]
            p_u_49._player_blob_manager:do_sync(function() --[[ Line: 262 ]]
                --[[ Upvalues: (ref 1): p_u_49, (ref 2): v_u_50, (ref 3): v_u_13, (ref 4): v_u_7, (copy 5): p_u_51 ]]
                p_u_49._menus:remove_menu(v_u_50)
                p_u_49._menus:push_menu(v_u_13:new(p_u_49, p_u_49._spui, p_u_49._menus, v_u_7.RewardInfo:table_to_list(p_u_51)):set_header_text("Challenge Pass Rewards Acquired!"))
            end)
        end)
        p_u_49._evt:fire_event_to_server(v_u_3.EVT_ChallengePassV2_ClientClaimRewards)
    end,
    ["show_robux_purchase_menu"] = function(_, p_u_52) --[[ Name: show_robux_purchase_menu ]] --[[ Line: 273 ]]
        --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_10, (copy 3): v_u_5, (copy 4): v_u_4, (copy 5): v_u_1, (copy 6): v_u_8, (copy 7): v_u_9, (copy 8): v_u_2, (ref 9): v_u_15, (copy 10): v_u_6 ]]
        local v_u_53 = nil
        v_u_53 = v_u_12:new(p_u_52, p_u_52._spui, p_u_52._menus, function(p54) --[[ Line: 280 ]]
            --[[ Upvalues: (copy 1): p_u_52, (ref 2): v_u_10, (ref 3): v_u_5, (ref 4): v_u_4 ]]
            p54:set_header_text("Purchase Upgrades")
            local v55 = p_u_52._player_blob_manager:get_player_blob()
            if v_u_10:playerblob_has_challengepass_vip_unlocked_for_dayid_monthid(v55, p_u_52._player_blob_manager:get_day_id(), p_u_52._player_blob_manager:get_month_id()) ~= true then
                p54:get_element_list():push_back(v_u_5.ProductID_ChallengePassV2UnlockVIPTier)
            end;
            p54:get_element_list():push_back(v_u_5.ProductID_ChallengePassV2Points250)
            p54:get_element_list():push_back(v_u_5.ProductID_ChallengePassV2Points500)
            p54:get_element_list():push_back(v_u_5.ProductID_ChallengePassV2Points1000)
            if v_u_4:playerblob_has_vip_for_current_day(v55, p_u_52._player_blob_manager:get_day_id()) ~= true then
                p54:get_element_list():push_back(-1)
            end;
        end, function(p56, p57, p58, _, p59) --[[ Line: 293 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_8, (ref 3): v_u_5, (ref 4): v_u_9 ]]
            if p56 == -1 then
                p57.Text = "Get RoBeats VIP!"
                p58.Image = v_u_1:get_iconhd_vip()
                p59:get_description_display().Text = "Purchase VIP to access Battle Pass VIP tier and more!"
            elseif v_u_8:test_enum_member(p56, v_u_5) then
                local v60 = v_u_5:get_info_data_for_productid(p56)
                p57.Text = v60:get_name()
                if p56 == v_u_5.ProductID_ChallengePassV2UnlockVIPTier then
                    p58.Image = v_u_1:important_assetid()
                else
                    p58.Image = v_u_9:get_challengepassv2_square_icon_assetid()
                end;
                p59:get_description_display().Text = string.format("%d Robux", v60:get_robux_cost())
                p59:set_select_button_enabled(true)
            end;
        end, function(p61) --[[ Line: 312 ]]
            --[[ Upvalues: (copy 1): p_u_52, (ref 2): v_u_2, (ref 3): v_u_15, (ref 4): v_u_8, (ref 5): v_u_5, (ref 6): v_u_6, (ref 7): v_u_53 ]]
            if p61 == nil then
                return;
            else
                p_u_52._sfx_manager:play_sfx(v_u_2.SFX_BUTTONPRESS)
                if p61 == -1 then
                    p_u_52._menus:push_menu(v_u_15:new(p_u_52, p_u_52._spui, p_u_52._menus))
                elseif v_u_8:test_enum_member(p61, v_u_5) then
                    v_u_6:purchase_prompt(p_u_52, p_u_52._spui, p_u_52._menus, p61, function() end)
                    p_u_52._menus:remove_menu(v_u_53)
                end;
            end;
        end):set_close_on_element_select(false):set_refresh_on_refocus(true)
        p_u_52._menus:push_menu(v_u_53)
    end
}
local v_u_63 = Color3.fromRGB(255, 255, 255)
local v_u_64 = Color3.fromRGB(199, 199, 199)
v_u_62.show_rewards_menu = function(p_u_65, p_u_66, p_u_67) --[[ Name: show_rewards_menu ]] --[[ Line: 197 ]]
    --[[ Upvalues: (copy 1): v_u_10, (ref 2): v_u_12, (copy 3): v_u_63, (copy 4): v_u_64, (copy 5): v_u_1 ]]
    local v_u_68 = p_u_66._player_blob_manager:get_player_blob()
    local v_u_69 = v_u_10:playerblob_get_points_total(v_u_68)
    local v_u_70 = nil
    local v83 = p_u_66._menus:push_menu(v_u_12:new(p_u_66, p_u_66._spui, p_u_66._menus, function(p71) --[[ Line: 205 ]]
        --[[ Upvalues: (copy 1): p_u_67, (ref 2): v_u_70, (copy 3): v_u_69 ]]
        p71:set_header_text("Challenge Pass Rewards")
        for _, v72 in p_u_67:key_itr() do
            if v_u_70 == nil and v_u_69 < v72:get_points() then
                v_u_70 = v72
            end;
            p71:get_element_list():push_back(v72)
        end;
    end, function(p73, p74, p75, _, p76, p77, _) --[[ Line: 214 ]]
        --[[ Upvalues: (ref 1): v_u_10, (copy 2): v_u_68, (copy 3): p_u_66, (ref 4): v_u_63, (ref 5): v_u_64, (copy 6): v_u_69, (ref 7): v_u_1 ]]
        p74.Text = string.format("Level #%d", p77)
        local v78 = v_u_10:playerblob_has_challengepass_vip_unlocked_for_dayid_monthid(v_u_68, p_u_66._player_blob_manager:get_day_id(), p_u_66._player_blob_manager:get_month_id())
        p75.Image = p73:get_icon(v78)
        p76:set_select_button_text("View")
        local v79
        if v78 then
            v79 = p77 <= v_u_10:playerblob_get_vip_claimed_tier(v_u_68)
        else
            v79 = p77 <= v_u_10:playerblob_get_standard_claimed_tier(v_u_68)
        end;
        p76:get_name_display().TextColor3 = v_u_63
        p76:get_description_display().TextColor3 = v_u_63
        if v79 then
            p76:get_description_display().Text = "Claimed"
            p76:get_name_display().TextColor3 = v_u_64
            p76:get_description_display().TextColor3 = v_u_64
            return;
        elseif v_u_69 >= p73:get_points() then
            p76:get_description_display().Text = "Ready to claim!"
        else
            p76:get_description_display().Text = string.format("%s Points", v_u_1:comma_value(p73:get_points()))
        end;
    end, function(p80, _, p81) --[[ Line: 243 ]]
        --[[ Upvalues: (copy 1): p_u_65, (copy 2): p_u_66 ]]
        if p80 ~= nil then
            p_u_65:show_challengepass_entry_rewards_menu(p_u_66, p80, p81:get_i_data())
        end;
    end, function(p82) --[[ Line: 247 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_10, (copy 3): v_u_68 ]]
        p82:set_sub_text(string.format("This Month: %s Points", v_u_1:comma_value(v_u_10:playerblob_get_points_total(v_u_68))))
    end)):set_close_on_element_select(false)
    if v_u_70 ~= nil then
        local v84 = v83:get_list_adapter()
        v84:go_to_page(v84:get_page_of_element(v_u_70))
    end;
end;
v_u_62.show_challengepass_main_menu_from_entry_list = function(_, p_u_85, p_u_86) --[[ Name: show_challengepass_main_menu_from_entry_list ]] --[[ Line: 329 ]]
    --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_1, (copy 3): v_u_63, (copy 4): v_u_10, (copy 5): v_u_64, (copy 6): v_u_9, (copy 7): v_u_62 ]]
    local v_u_87 = p_u_85._player_blob_manager:get_player_blob()
    p_u_85._menus:push_menu(v_u_12:new(p_u_85, p_u_85._spui, p_u_85._menus, function(p88) --[[ Line: 342 ]]
        p88:set_header_text("Challenge Pass")
        p88:get_element_list():push_back(-1)
        p88:get_element_list():push_back(-4)
        p88:get_element_list():push_back(-2)
        p88:get_element_list():push_back(-3)
        p88:get_element_list():push_back(-5)
        p88:get_element_list():push_back(-6)
    end, function(p89, p90, p91, _, p92) --[[ Line: 351 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_63, (ref 3): v_u_10, (copy 4): v_u_87, (copy 5): p_u_86, (copy 6): p_u_85, (ref 7): v_u_64, (ref 8): v_u_9 ]]
        p91.Image = v_u_1:important_assetid()
        p91.ImageRectOffset = Vector2.new(0, 0)
        p91.ImageRectSize = Vector2.new(0, 0)
        p92:get_name_display().TextColor3 = v_u_63
        p92:get_description_display().TextColor3 = v_u_63
        if p89 == -1 then
            p90.Text = "Claim Rewards"
            p91.Image = v_u_1:important_assetid()
            local v93, v94 = v_u_10:playerblob_has_any_claimable_rewards_for_day_month(v_u_87, p_u_86, p_u_85._player_blob_manager:get_day_id(), p_u_85._player_blob_manager:get_month_id())
            p92:set_select_button_text("Claim")
            if v93 then
                p92:set_select_button_enabled(true)
                p92:get_description_display().Text = string.format("%d reward(s) ready to claim!", v94)
            else
                p92:set_select_button_enabled(false)
                p92:get_description_display().Text = ""
                p92:get_name_display().TextColor3 = v_u_64
                p92:get_description_display().TextColor3 = v_u_64
            end;
        end;
        if p89 == -2 then
            p90.Text = "Daily Tasks"
            p91.Image = "rbxassetid://1138396569"
            p91.ImageRectOffset = Vector2.new(2, 0)
            p91.ImageRectSize = Vector2.new(55, 55)
            p92:get_description_display().Text = string.format("%s / %s points claimed today.", v_u_1:comma_value(v_u_10:playerblob_get_daily_mission_points(v_u_87)), v_u_1:comma_value(v_u_10:get_daily_point_cap()))
            p92:set_select_button_text("View")
            return;
        end;
        if p89 == -3 then
            p90.Text = "Weekly Tasks"
            p91.Image = "rbxassetid://1138396570"
            p91.ImageRectOffset = Vector2.new(6, 0)
            p91.ImageRectSize = Vector2.new(55, 55)
            p92:get_description_display().Text = string.format("%s / %s points claimed this week.", v_u_1:comma_value(v_u_10:playerblob_get_weekly_mission_points(v_u_87)), v_u_1:comma_value(v_u_10:get_weekly_point_cap()))
            p92:set_select_button_text("View")
            return;
        end;
        if p89 ~= -4 then
            if p89 == -5 then
                p90.Text = "Purchase Upgrades"
                p91.Image = v_u_1:get_iconhd_trophy()
                p92:get_description_display().Text = "Unlock VIP tier and extra points!"
                p92:set_select_button_text("Buy")
            elseif p89 == -6 then
                p90.Text = "Time Remaining"
                p91.Image = v_u_1:gear_assetid()
                p92:get_description_display().Text = v_u_1:format_sec_time(p_u_85._player_blob_manager:get_time_to_next_month_sec())
                p92:set_select_button_enabled(false)
                p92:set_select_button_text("-")
            end;
        end;
        p90.Text = "View Reward Levels"
        p91.Image = v_u_9:get_challengepassv2_square_icon_assetid()
        local v95 = v_u_10:playerblob_get_points_total(v_u_87)
        local v96 = -1
        for _, v97 in p_u_86:key_itr() do
            if v95 < v97:get_points() then
                v96 = v97:get_points()
                break;
            end;
        end;
        if v96 > 0 then
            p92:get_description_display().Text = string.format("Next reward at %s points.", v_u_1:comma_value(v96))
        else
            p92:get_description_display().Text = ""
        end;
        p92:set_select_button_text("View")
    end, function(p98) --[[ Line: 435 ]]
        --[[ Upvalues: (ref 1): v_u_62, (copy 2): p_u_85, (copy 3): p_u_86 ]]
        if p98 == nil then
            return;
        elseif p98 == -1 then
            v_u_62:claim_challengepass_rewards(p_u_85)
            return;
        elseif p98 == -2 then
            v_u_62:show_daily_missions_menu(p_u_85)
            return;
        elseif p98 == -3 then
            v_u_62:show_weekly_missions_menu(p_u_85)
            return;
        elseif p98 == -4 then
            v_u_62:show_rewards_menu(p_u_85, p_u_86)
        elseif p98 == -5 then
            v_u_62:show_robux_purchase_menu(p_u_85)
        end;
    end, function(p99) --[[ Line: 449 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_10, (copy 3): v_u_87 ]]
        p99:set_sub_text(string.format("This Month: %s Points", v_u_1:comma_value(v_u_10:playerblob_get_points_total(v_u_87))))
    end)):set_close_on_element_select(false):add_fn_element_behaviour_update(function(p100) --[[ Line: 454 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_85 ]]
        if p100:get_data() == -6 then
            p100:get_description_display().Text = v_u_1:format_sec_time(p_u_85._player_blob_manager:get_time_to_next_month_sec())
        end;
    end)
end;
v_u_62.show_challengepass_menu = function(_, p_u_101) --[[ Name: show_challengepass_menu ]] --[[ Line: 461 ]]
    --[[ Upvalues: (ref 1): v_u_14, (copy 2): v_u_62 ]]
    local v_u_102 = p_u_101._menus:push_menu(v_u_14:new(p_u_101, p_u_101._spui, p_u_101._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
    p_u_101._shop_local_protocol:request_challengepassv2_entry_list(function(p103) --[[ Line: 463 ]]
        --[[ Upvalues: (copy 1): p_u_101, (copy 2): v_u_102, (ref 3): v_u_62 ]]
        p_u_101._menus:remove_menu(v_u_102)
        v_u_62:show_challengepass_main_menu_from_entry_list(p_u_101, p103)
    end)
end;
return v_u_62;
