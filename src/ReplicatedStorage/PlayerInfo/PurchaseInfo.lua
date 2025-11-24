-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:04 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.PlayerInfo.SaleInfo)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.DayEventInfo)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v7 = require(game.ReplicatedStorage.Shared.SPDict)
local v8 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v9 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_10 = nil
local v_u_11 = nil
v9:require_client(function() --[[ Line: 15 ]]
    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_11 ]]
    v_u_10 = require(game.ReplicatedStorage.PlayerInfo.PurchaseInfoRewardDescription)
    v_u_11 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
end)
local v_u_12 = {
    ["ProductID_None"] = 0,
    ["DEPRECATED_ProductID_Star1"] = 86000833,
    ["DEPRECATED_ProductID_Star2"] = 86000867,
    ["DEPRECATED_ProductID_Star3"] = 86000896,
    ["DEPRECATED_ProductID_Coin1"] = 86000729,
    ["DEPRECATED_ProductID_Coin2"] = 86000756,
    ["DEPRECATED_ProductID_Coin3"] = 86000788,
    ["DEPRECATED_ProductID_StarterPack"] = 86000925,
    ["ProductID_LeavePenaltyClear5"] = 149336052,
    ["ProductID_LeavePenaltyClear10"] = 149336384,
    ["ProductID_LeavePenaltyClear30"] = 149336718,
    ["ProductID_Star1_V3"] = 475652135,
    ["ProductID_Star2_V3"] = 475653584,
    ["ProductID_Star3_V3"] = 475653924,
    ["ProductID_Star4_V3"] = 475654231,
    ["ProductID_Coin1_V3"] = 475654890,
    ["ProductID_Coin2_V3"] = 475655242,
    ["ProductID_Coin3_V3"] = 475655762,
    ["ProductID_Coin4_V3"] = 475656086,
    ["ProductID_Star1_V3_Sale50"] = 1035847804,
    ["ProductID_Star2_V3_Sale50"] = 1035849460,
    ["ProductID_Star3_V3_Sale50"] = 1035852196,
    ["ProductID_Star4_V3_Sale50"] = 1035853890,
    ["ProductID_Coin1_V3_Sale50"] = 1035863395,
    ["ProductID_Coin2_V3_Sale50"] = 1035864864,
    ["ProductID_Coin3_V3_Sale50"] = 1035868479,
    ["ProductID_Coin4_V3_Sale50"] = 1035870210,
    ["ProductID_StarterPack_V3"] = 475657437,
    ["ProductID_CoinPack_V3"] = 475657991,
    ["ProductID_StarPack_V3"] = 475658238,
    ["ProductID_StarterPack_V3_Sale50"] = 1035879997,
    ["ProductID_CoinPack_V3_Sale50"] = 1035881611,
    ["ProductID_StarPack_V3_Sale50"] = 1035883621,
    ["ProductID_VIP_1Month"] = 1086217067,
    ["ProductID_VIP_3Month"] = 489193981,
    ["ProductID_VIP_6Month"] = 489194500,
    ["ProductID_VIP_1Month_Sale50"] = 1033869763,
    ["ProductID_VIP_3Month_Sale50"] = 1033871601,
    ["ProductID_VIP_6Month_Sale50"] = 1033872570,
    ["ProductID_ChallengePassSeasonUnlock"] = 891577868,
    ["ProductID_ChallengePassComplete"] = 891580459,
    ["ProductID_EventPoint1000"] = 1201674407,
    ["ProductID_EventPoint2000"] = 1249973252,
    ["ProductID_ChallengePassV2UnlockVIPTier"] = 1748041432,
    ["ProductID_ChallengePassV2Points250"] = 1748042279,
    ["ProductID_ChallengePassV2Points500"] = 1748042442,
    ["ProductID_ChallengePassV2Points1000"] = 1748042658,
    ["ProductID_UpgradeBoost_5"] = 637457214,
    ["ProductID_UpgradeBoost_5_Sale50"] = 1296367164,
    ["ProductID_UpgradeBoost_20"] = 1296367520,
    ["ProductID_UpgradeBoost_20_Sale50"] = 1296367612,
    ["ProductID_UpgradeBoost_50"] = 1296367743,
    ["ProductID_UpgradeBoost_50_Sale50"] = 1296367839,
    ["ProductID_UpgradeBoost_100"] = 1296368172,
    ["ProductID_UpgradeBoost_100_Sale50"] = 1296368227,
    ["ProductID_UpgradeProtect_5"] = 637456790,
    ["ProductID_UpgradeProtect_5_Sale50"] = 1296368717,
    ["ProductID_UpgradeProtect_20"] = 1296368853,
    ["ProductID_UpgradeProtect_20_Sale50"] = 1296368949,
    ["ProductID_UpgradeProtect_50"] = 1296369085,
    ["ProductID_UpgradeProtect_50_Sale50"] = 1296369185,
    ["ProductID_UpgradeProtect_100"] = 1296369638,
    ["ProductID_UpgradeProtect_100_Sale50"] = 1296369757,
    ["ProductID_GemBox_10"] = 1296370175,
    ["ProductID_GemBox_10_Sale50"] = 1296370232,
    ["ProductID_GemBox_30"] = 1296370317,
    ["ProductID_GemBox_30_Sale50"] = 1296370386,
    ["ProductID_GemBox_100"] = 1296370543,
    ["ProductID_GemBox_100_Sale50"] = 1296370623,
    ["ProductID_GemBox_225"] = 1296370813,
    ["ProductID_GemBox_225_Sale50"] = 1296370901,
    ["ProductID_TokenBox_1"] = 1296371225,
    ["ProductID_TokenBox_1_Sale50"] = 1296371304,
    ["ProductID_TokenBox_5"] = 1296371443,
    ["ProductID_TokenBox_5_Sale50"] = 1296371534,
    ["ProductID_TokenBox_10"] = 1296371632,
    ["ProductID_TokenBox_10_Sale50"] = 1296371692,
    ["ProductID_TokenBox_20"] = 1296371872,
    ["ProductID_TokenBox_20_Sale50"] = 1296371949,
    ["ProductID_Mini1StarBox_5"] = 1296372357,
    ["ProductID_Mini1StarBox_5_Sale50"] = 1296372465,
    ["ProductID_Mini1StarBox_15"] = 1296372624,
    ["ProductID_Mini1StarBox_15_Sale50"] = 1296372688,
    ["ProductID_Mini1StarBox_40"] = 1296372788,
    ["ProductID_Mini1StarBox_40_Sale50"] = 1296372837,
    ["ProductID_Mini1StarBox_80"] = 1296372948,
    ["ProductID_Mini1StarBox_80_Sale50"] = 1296372991,
    ["ProductID_Mini2StarBox_1"] = 1296373341,
    ["ProductID_Mini2StarBox_1_Sale50"] = 1296373387,
    ["ProductID_Mini2StarBox_5"] = 1296373502,
    ["ProductID_Mini2StarBox_5_Sale50"] = 1296373606,
    ["ProductID_Mini2StarBox_15"] = 1296373704,
    ["ProductID_Mini2StarBox_15_Sale50"] = 1296373843,
    ["ProductID_Mini2StarBox_35"] = 1296373915,
    ["ProductID_Mini2StarBox_35_Sale50"] = 1296374000
}
local v_u_13 = {
    {
        ["Name"] = "15 Stars",
        ["DisplayIcon"] = "rbxassetid://10519187871",
        ["ProductID"] = v_u_12.ProductID_Star1_V3,
        ["RobuxCost"] = 50
    },
    {
        ["Name"] = "15 Stars (SALE!)",
        ["ProductID"] = v_u_12.ProductID_Star1_V3_Sale50,
        ["RobuxCost"] = 25,
        ["RequiresDayEvent"] = v_u_6.EventType.StarSale,
        ["CopyFrom"] = v_u_12.ProductID_Star1_V3
    },
    {
        ["Name"] = "35 Stars",
        ["DisplayIcon"] = "rbxassetid://10519187949",
        ["ProductID"] = v_u_12.ProductID_Star2_V3,
        ["RobuxCost"] = 100
    },
    {
        ["Name"] = "35 Stars (SALE!)",
        ["ProductID"] = v_u_12.ProductID_Star2_V3_Sale50,
        ["RobuxCost"] = 50,
        ["RequiresDayEvent"] = v_u_6.EventType.StarSale,
        ["CopyFrom"] = v_u_12.ProductID_Star2_V3
    },
    {
        ["Name"] = "200 Stars",
        ["DisplayIcon"] = "rbxassetid://10519188046",
        ["ProductID"] = v_u_12.ProductID_Star3_V3,
        ["RobuxCost"] = 500
    },
    {
        ["Name"] = "200 Stars (SALE!)",
        ["ProductID"] = v_u_12.ProductID_Star3_V3_Sale50,
        ["RobuxCost"] = 250,
        ["RequiresDayEvent"] = v_u_6.EventType.StarSale,
        ["CopyFrom"] = v_u_12.ProductID_Star3_V3
    },
    {
        ["Name"] = "425 Stars",
        ["DisplayIcon"] = "rbxassetid://10519188197",
        ["ProductID"] = v_u_12.ProductID_Star4_V3,
        ["RobuxCost"] = 1000
    },
    {
        ["Name"] = "425 Stars (SALE!)",
        ["ProductID"] = v_u_12.ProductID_Star4_V3_Sale50,
        ["RobuxCost"] = 500,
        ["RequiresDayEvent"] = v_u_6.EventType.StarSale,
        ["CopyFrom"] = v_u_12.ProductID_Star4_V3
    },
    {
        ["Name"] = "1,000 Coins",
        ["DisplayIcon"] = "rbxassetid://10519187395",
        ["ProductID"] = v_u_12.ProductID_Coin1_V3,
        ["RobuxCost"] = 50
    },
    {
        ["Name"] = "1,000 Coins (SALE!)",
        ["ProductID"] = v_u_12.ProductID_Coin1_V3_Sale50,
        ["RobuxCost"] = 25,
        ["RequiresDayEvent"] = v_u_6.EventType.CoinSale,
        ["CopyFrom"] = v_u_12.ProductID_Coin1_V3
    },
    {
        ["Name"] = "2,250 Coins",
        ["DisplayIcon"] = "rbxassetid://10519187547",
        ["ProductID"] = v_u_12.ProductID_Coin2_V3,
        ["RobuxCost"] = 100
    },
    {
        ["Name"] = "2,250 Coins (SALE!)",
        ["ProductID"] = v_u_12.ProductID_Coin2_V3_Sale50,
        ["RobuxCost"] = 50,
        ["RequiresDayEvent"] = v_u_6.EventType.CoinSale,
        ["CopyFrom"] = v_u_12.ProductID_Coin2_V3
    },
    {
        ["Name"] = "12,000 Coins",
        ["DisplayIcon"] = "rbxassetid://10519187668",
        ["ProductID"] = v_u_12.ProductID_Coin3_V3,
        ["RobuxCost"] = 500
    },
    {
        ["Name"] = "12,000 Coins (SALE!)",
        ["ProductID"] = v_u_12.ProductID_Coin3_V3_Sale50,
        ["RobuxCost"] = 250,
        ["RequiresDayEvent"] = v_u_6.EventType.CoinSale,
        ["CopyFrom"] = v_u_12.ProductID_Coin3_V3
    },
    {
        ["Name"] = "25,000 Coins",
        ["DisplayIcon"] = "rbxassetid://10519187775",
        ["ProductID"] = v_u_12.ProductID_Coin4_V3,
        ["RobuxCost"] = 1000
    },
    {
        ["Name"] = "25,000 Coins (SALE!)",
        ["ProductID"] = v_u_12.ProductID_Coin4_V3_Sale50,
        ["RobuxCost"] = 500,
        ["RequiresDayEvent"] = v_u_6.EventType.CoinSale,
        ["CopyFrom"] = v_u_12.ProductID_Coin4_V3
    },
    {
        ["Name"] = "Starter Pack",
        ["DisplayIcon"] = "rbxassetid://10529293223",
        ["ProductID"] = v_u_12.ProductID_StarterPack_V3,
        ["RobuxCost"] = 500
    },
    {
        ["Name"] = "Starter Pack (SALE!)",
        ["ProductID"] = v_u_12.ProductID_StarterPack_V3_Sale50,
        ["RobuxCost"] = 250,
        ["RequiresDayEvent"] = v_u_6.EventType.PackSale,
        ["CopyFrom"] = v_u_12.ProductID_StarterPack_V3
    },
    {
        ["Name"] = "Coin Pack",
        ["DisplayIcon"] = "rbxassetid://10529293725",
        ["ProductID"] = v_u_12.ProductID_CoinPack_V3,
        ["RobuxCost"] = 500
    },
    {
        ["Name"] = "Coin Pack (SALE!)",
        ["ProductID"] = v_u_12.ProductID_CoinPack_V3_Sale50,
        ["RobuxCost"] = 250,
        ["RequiresDayEvent"] = v_u_6.EventType.PackSale,
        ["CopyFrom"] = v_u_12.ProductID_CoinPack_V3
    },
    {
        ["Name"] = "Star Pack",
        ["DisplayIcon"] = "rbxassetid://10529293502",
        ["ProductID"] = v_u_12.ProductID_StarPack_V3,
        ["RobuxCost"] = 500
    },
    {
        ["Name"] = "Star Pack (SALE!)",
        ["ProductID"] = v_u_12.ProductID_StarPack_V3_Sale50,
        ["RobuxCost"] = 250,
        ["RequiresDayEvent"] = v_u_6.EventType.PackSale,
        ["CopyFrom"] = v_u_12.ProductID_StarPack_V3
    },
    {
        ["Name"] = "1 Month VIP",
        ["ProductID"] = v_u_12.ProductID_VIP_1Month,
        ["RobuxCost"] = 450
    },
    {
        ["Name"] = "1 Month VIP (SALE!)",
        ["ProductID"] = v_u_12.ProductID_VIP_1Month_Sale50,
        ["RobuxCost"] = 250,
        ["RequiresDayEvent"] = v_u_6.EventType.VIPSale,
        ["CopyFrom"] = v_u_12.ProductID_VIP_1Month
    },
    {
        ["Name"] = "3 Month VIP",
        ["ProductID"] = v_u_12.ProductID_VIP_3Month,
        ["RobuxCost"] = 1250
    },
    {
        ["Name"] = "3 Month VIP (SALE!)",
        ["ProductID"] = v_u_12.ProductID_VIP_3Month_Sale50,
        ["RobuxCost"] = 625,
        ["RequiresDayEvent"] = v_u_6.EventType.VIPSale,
        ["CopyFrom"] = v_u_12.ProductID_VIP_3Month
    },
    {
        ["Name"] = "6 Month VIP",
        ["ProductID"] = v_u_12.ProductID_VIP_6Month,
        ["RobuxCost"] = 2250
    },
    {
        ["Name"] = "6 Month VIP (SALE!)",
        ["ProductID"] = v_u_12.ProductID_VIP_6Month_Sale50,
        ["RobuxCost"] = 1125,
        ["RequiresDayEvent"] = v_u_6.EventType.VIPSale,
        ["CopyFrom"] = v_u_12.ProductID_VIP_6Month
    },
    {
        ["Name"] = "Unlock Current VIP Challenge Pass",
        ["ProductID"] = v_u_12.ProductID_ChallengePassSeasonUnlock,
        ["RobuxCost"] = 100
    },
    {
        ["Name"] = "Complete Current Challenge Pass Tier",
        ["ProductID"] = v_u_12.ProductID_ChallengePassComplete,
        ["RobuxCost"] = 50
    },
    {
        ["Name"] = "1000 Event Points",
        ["ProductID"] = v_u_12.ProductID_EventPoint1000,
        ["RobuxCost"] = 50
    },
    {
        ["Name"] = "2000 Event Points",
        ["ProductID"] = v_u_12.ProductID_EventPoint2000,
        ["RobuxCost"] = 100
    },
    {
        ["Name"] = "Unlock Challenge Pass VIP Tier",
        ["ProductID"] = v_u_12.ProductID_ChallengePassV2UnlockVIPTier,
        ["RobuxCost"] = 100
    },
    {
        ["Name"] = "250 Challenge Pass Points",
        ["ProductID"] = v_u_12.ProductID_ChallengePassV2Points250,
        ["RobuxCost"] = 100
    },
    {
        ["Name"] = "500 Challenge Pass Points",
        ["ProductID"] = v_u_12.ProductID_ChallengePassV2Points500,
        ["RobuxCost"] = 200
    },
    {
        ["Name"] = "1000 Challenge Pass Points",
        ["ProductID"] = v_u_12.ProductID_ChallengePassV2Points1000,
        ["RobuxCost"] = 400
    },
    {
        ["Name"] = "Upgrade Boosts x5",
        ["ProductID"] = v_u_12.ProductID_UpgradeBoost_5,
        ["RobuxCost"] = 100,
        ["DisplayIcon"] = "rbxassetid://10519188396"
    },
    {
        ["Name"] = "Upgrade Boost x5 (SALE!)",
        ["RobuxCost"] = 75,
        ["ProductID"] = v_u_12.ProductID_UpgradeBoost_5_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.UpgradeSale,
        ["CopyFrom"] = v_u_12.ProductID_UpgradeBoost_5
    },
    {
        ["Name"] = "Upgrade Boost x20",
        ["RobuxCost"] = 350,
        ["ProductID"] = v_u_12.ProductID_UpgradeBoost_20,
        ["DisplayIcon"] = "rbxassetid://10519188559"
    },
    {
        ["Name"] = "Upgrade Boost x20 (SALE!)",
        ["RobuxCost"] = 260,
        ["ProductID"] = v_u_12.ProductID_UpgradeBoost_20_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.UpgradeSale,
        ["CopyFrom"] = v_u_12.ProductID_UpgradeBoost_20
    },
    {
        ["Name"] = "Upgrade Boost x50",
        ["RobuxCost"] = 750,
        ["ProductID"] = v_u_12.ProductID_UpgradeBoost_50,
        ["DisplayIcon"] = "rbxassetid://10519188730"
    },
    {
        ["Name"] = "Upgrade Boost x50 (SALE!)",
        ["RobuxCost"] = 560,
        ["ProductID"] = v_u_12.ProductID_UpgradeBoost_50_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.UpgradeSale,
        ["CopyFrom"] = v_u_12.ProductID_UpgradeBoost_50
    },
    {
        ["Name"] = "Upgrade Boost x100",
        ["RobuxCost"] = 1250,
        ["ProductID"] = v_u_12.ProductID_UpgradeBoost_100,
        ["DisplayIcon"] = "rbxassetid://10519188872"
    },
    {
        ["Name"] = "Upgrade Boost x100 (SALE!)",
        ["RobuxCost"] = 930,
        ["ProductID"] = v_u_12.ProductID_UpgradeBoost_100_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.UpgradeSale,
        ["CopyFrom"] = v_u_12.ProductID_UpgradeBoost_100
    },
    {
        ["Name"] = "Upgrade Protects x5",
        ["ProductID"] = v_u_12.ProductID_UpgradeProtect_5,
        ["RobuxCost"] = 100,
        ["DisplayIcon"] = "rbxassetid://10519189029"
    },
    {
        ["Name"] = "Upgrade Protect x5 (SALE!)",
        ["RobuxCost"] = 75,
        ["ProductID"] = v_u_12.ProductID_UpgradeProtect_5_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.UpgradeSale,
        ["CopyFrom"] = v_u_12.ProductID_UpgradeProtect_5
    },
    {
        ["Name"] = "Upgrade Protect x20",
        ["RobuxCost"] = 350,
        ["ProductID"] = v_u_12.ProductID_UpgradeProtect_20,
        ["DisplayIcon"] = "rbxassetid://10519189232"
    },
    {
        ["Name"] = "Upgrade Protect x20 (SALE!)",
        ["RobuxCost"] = 260,
        ["ProductID"] = v_u_12.ProductID_UpgradeProtect_20_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.UpgradeSale,
        ["CopyFrom"] = v_u_12.ProductID_UpgradeProtect_20
    },
    {
        ["Name"] = "Upgrade Protect x50",
        ["RobuxCost"] = 750,
        ["ProductID"] = v_u_12.ProductID_UpgradeProtect_50,
        ["DisplayIcon"] = "rbxassetid://10519189407"
    },
    {
        ["Name"] = "Upgrade Protect x50 (SALE!)",
        ["RobuxCost"] = 560,
        ["ProductID"] = v_u_12.ProductID_UpgradeProtect_50_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.UpgradeSale,
        ["CopyFrom"] = v_u_12.ProductID_UpgradeProtect_50
    },
    {
        ["Name"] = "Upgrade Protect x100",
        ["RobuxCost"] = 1250,
        ["ProductID"] = v_u_12.ProductID_UpgradeProtect_100,
        ["DisplayIcon"] = "rbxassetid://10519189572"
    },
    {
        ["Name"] = "Upgrade Protect x100 (SALE!)",
        ["RobuxCost"] = 930,
        ["ProductID"] = v_u_12.ProductID_UpgradeProtect_100_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.UpgradeSale,
        ["CopyFrom"] = v_u_12.ProductID_UpgradeProtect_100
    },
    {
        ["Name"] = "Gem Box x10",
        ["RobuxCost"] = 100,
        ["ProductID"] = v_u_12.ProductID_GemBox_10,
        ["DisplayIcon"] = "rbxassetid://10519189737"
    },
    {
        ["Name"] = "Gem Box x10 (SALE!)",
        ["RobuxCost"] = 75,
        ["ProductID"] = v_u_12.ProductID_GemBox_10_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.CraftSale,
        ["CopyFrom"] = v_u_12.ProductID_GemBox_10
    },
    {
        ["Name"] = "Gem Box x30",
        ["RobuxCost"] = 250,
        ["ProductID"] = v_u_12.ProductID_GemBox_30,
        ["DisplayIcon"] = "rbxassetid://10519189945"
    },
    {
        ["Name"] = "Gem Box x30 (SALE!)",
        ["RobuxCost"] = 185,
        ["ProductID"] = v_u_12.ProductID_GemBox_30_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.CraftSale,
        ["CopyFrom"] = v_u_12.ProductID_GemBox_30
    },
    {
        ["Name"] = "Gem Box x100",
        ["RobuxCost"] = 750,
        ["ProductID"] = v_u_12.ProductID_GemBox_100,
        ["DisplayIcon"] = "rbxassetid://10519190127"
    },
    {
        ["Name"] = "Gem Box x100 (SALE!)",
        ["RobuxCost"] = 560,
        ["ProductID"] = v_u_12.ProductID_GemBox_100_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.CraftSale,
        ["CopyFrom"] = v_u_12.ProductID_GemBox_100
    },
    {
        ["Name"] = "Gem Box x225",
        ["RobuxCost"] = 1500,
        ["ProductID"] = v_u_12.ProductID_GemBox_225,
        ["DisplayIcon"] = "rbxassetid://10519190308"
    },
    {
        ["Name"] = "Gem Box x225 (SALE!)",
        ["RobuxCost"] = 1125,
        ["ProductID"] = v_u_12.ProductID_GemBox_225_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.CraftSale,
        ["CopyFrom"] = v_u_12.ProductID_GemBox_225
    },
    {
        ["Name"] = "Token Box x1",
        ["RobuxCost"] = 50,
        ["ProductID"] = v_u_12.ProductID_TokenBox_1,
        ["DisplayIcon"] = "rbxassetid://10519190426"
    },
    {
        ["Name"] = "Token Box x1 (SALE!)",
        ["RobuxCost"] = 40,
        ["ProductID"] = v_u_12.ProductID_TokenBox_1_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.CraftSale,
        ["CopyFrom"] = v_u_12.ProductID_TokenBox_1
    },
    {
        ["Name"] = "Token Box x5",
        ["RobuxCost"] = 225,
        ["ProductID"] = v_u_12.ProductID_TokenBox_5,
        ["DisplayIcon"] = "rbxassetid://10519190522"
    },
    {
        ["Name"] = "Token Box x5 (SALE!)",
        ["RobuxCost"] = 165,
        ["ProductID"] = v_u_12.ProductID_TokenBox_5_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.CraftSale,
        ["CopyFrom"] = v_u_12.ProductID_TokenBox_5
    },
    {
        ["Name"] = "Token Box x10",
        ["RobuxCost"] = 400,
        ["ProductID"] = v_u_12.ProductID_TokenBox_10,
        ["DisplayIcon"] = "rbxassetid://10519190663"
    },
    {
        ["Name"] = "Token Box x10 (SALE!)",
        ["RobuxCost"] = 300,
        ["ProductID"] = v_u_12.ProductID_TokenBox_10_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.CraftSale,
        ["CopyFrom"] = v_u_12.ProductID_TokenBox_10
    },
    {
        ["Name"] = "Token Box x20",
        ["RobuxCost"] = 750,
        ["ProductID"] = v_u_12.ProductID_TokenBox_20,
        ["DisplayIcon"] = "rbxassetid://10519190778"
    },
    {
        ["Name"] = "Token Box x20 (SALE!)",
        ["RobuxCost"] = 560,
        ["ProductID"] = v_u_12.ProductID_TokenBox_20_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.CraftSale,
        ["CopyFrom"] = v_u_12.ProductID_TokenBox_20
    },
    {
        ["Name"] = "Mini 1-Star Box x5",
        ["RobuxCost"] = 65,
        ["ProductID"] = v_u_12.ProductID_Mini1StarBox_5,
        ["DisplayIcon"] = "rbxassetid://10519190914"
    },
    {
        ["Name"] = "Mini 1-Star Box x5 (SALE!)",
        ["RobuxCost"] = 50,
        ["ProductID"] = v_u_12.ProductID_Mini1StarBox_5_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.MiniSale,
        ["CopyFrom"] = v_u_12.ProductID_Mini1StarBox_5
    },
    {
        ["Name"] = "Mini 1-Star Box x15",
        ["RobuxCost"] = 165,
        ["ProductID"] = v_u_12.ProductID_Mini1StarBox_15,
        ["DisplayIcon"] = "rbxassetid://10519191090"
    },
    {
        ["Name"] = "Mini 1-Star Box x15 (SALE!)",
        ["RobuxCost"] = 125,
        ["ProductID"] = v_u_12.ProductID_Mini1StarBox_15_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.MiniSale,
        ["CopyFrom"] = v_u_12.ProductID_Mini1StarBox_15
    },
    {
        ["Name"] = "Mini 1-Star Box x40",
        ["RobuxCost"] = 400,
        ["ProductID"] = v_u_12.ProductID_Mini1StarBox_40,
        ["DisplayIcon"] = "rbxassetid://10519191208"
    },
    {
        ["Name"] = "Mini 1-Star Box x40 (SALE!)",
        ["RobuxCost"] = 300,
        ["ProductID"] = v_u_12.ProductID_Mini1StarBox_40_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.MiniSale,
        ["CopyFrom"] = v_u_12.ProductID_Mini1StarBox_40
    },
    {
        ["Name"] = "Mini 1-Star Box x80",
        ["RobuxCost"] = 720,
        ["ProductID"] = v_u_12.ProductID_Mini1StarBox_80,
        ["DisplayIcon"] = "rbxassetid://10519191415"
    },
    {
        ["Name"] = "Mini 1-Star Box x80 (SALE!)",
        ["RobuxCost"] = 540,
        ["ProductID"] = v_u_12.ProductID_Mini1StarBox_80_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.MiniSale,
        ["CopyFrom"] = v_u_12.ProductID_Mini1StarBox_80
    },
    {
        ["Name"] = "Mini 2-Star Box x1",
        ["RobuxCost"] = 30,
        ["ProductID"] = v_u_12.ProductID_Mini2StarBox_1,
        ["DisplayIcon"] = "rbxassetid://10519191551"
    },
    {
        ["Name"] = "Mini 2-Star Box x1 (SALE!)",
        ["RobuxCost"] = 25,
        ["ProductID"] = v_u_12.ProductID_Mini2StarBox_1_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.MiniSale,
        ["CopyFrom"] = v_u_12.ProductID_Mini2StarBox_1
    },
    {
        ["Name"] = "Mini 2-Star Box x5",
        ["RobuxCost"] = 135,
        ["ProductID"] = v_u_12.ProductID_Mini2StarBox_5,
        ["DisplayIcon"] = "rbxassetid://10519191674"
    },
    {
        ["Name"] = "Mini 2-Star Box x5 (SALE!)",
        ["RobuxCost"] = 100,
        ["ProductID"] = v_u_12.ProductID_Mini2StarBox_5_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.MiniSale,
        ["CopyFrom"] = v_u_12.ProductID_Mini2StarBox_5
    },
    {
        ["Name"] = "Mini 2-Star Box x15",
        ["RobuxCost"] = 375,
        ["ProductID"] = v_u_12.ProductID_Mini2StarBox_15,
        ["DisplayIcon"] = "rbxassetid://10519191772"
    },
    {
        ["Name"] = "Mini 2-Star Box x15 (SALE!)",
        ["RobuxCost"] = 280,
        ["ProductID"] = v_u_12.ProductID_Mini2StarBox_15_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.MiniSale,
        ["CopyFrom"] = v_u_12.ProductID_Mini2StarBox_15
    },
    {
        ["Name"] = "Mini 2-Star Box x35",
        ["RobuxCost"] = 900,
        ["ProductID"] = v_u_12.ProductID_Mini2StarBox_35,
        ["DisplayIcon"] = "rbxassetid://10519191861"
    },
    {
        ["Name"] = "Mini 2-Star Box x35 (SALE!)",
        ["RobuxCost"] = 675,
        ["ProductID"] = v_u_12.ProductID_Mini2StarBox_35_Sale50,
        ["RequiresDayEvent"] = v_u_6.EventType.MiniSale,
        ["CopyFrom"] = v_u_12.ProductID_Mini2StarBox_35
    }
}
v_u_12.get_purchase_info_definitions_table = function(_) --[[ Name: get_purchase_info_definitions_table ]] --[[ Line: 579 ]]
    --[[ Upvalues: (copy 1): v_u_13 ]]
    return v_u_13;
end;
local v_u_14 = v7:new()
v_u_12.get_copy_from_product_ids_map = function(_) --[[ Name: get_copy_from_product_ids_map ]] --[[ Line: 582 ]]
    --[[ Upvalues: (copy 1): v_u_14 ]]
    return v_u_14;
end;
local v15 = v7:new()
local v_u_16 = v_u_11
local v_u_17 = v_u_10
for _, v18 in pairs(v_u_13) do
    v15:add(v18.ProductID, v18)
end;
local v19 = v7:new()
for _, v20 in pairs(v_u_13) do
    if v20.CopyFrom ~= nil then
        v_u_4:is_enum_member(v20.CopyFrom, v_u_12)
        v_u_4:is_enum_member(v20.RequiresDayEvent, v_u_6.EventType)
        v_u_4:is_false(v19:contains(v20.CopyFrom))
        local v21 = v15:get(v20.CopyFrom)
        if v21.CopyFrom ~= nil then
            v_u_4:is_true(v21.CopyFrom == nil, string.format("src(%s) dest(%s)", v_u_5:table_to_string(v21), v_u_5:table_to_string(v20)))
        end;
        v_u_14:add(v20.ProductID, v21.ProductID)
        v19:add_set(v20.CopyFrom)
        v20.DisplayIcon = v21.DisplayIcon
    end;
end;
local v_u_22 = v7:new()
local v23 = {}
v23.new = function(_, p_u_24) --[[ Name: new ]] --[[ Line: 620 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_12, (copy 3): v_u_6, (copy 4): v_u_5, (ref 5): v_u_17, (ref 6): v_u_16 ]]
    local v25 = {}
    local l_Name_0 = p_u_24.Name
    v_u_4:is_string(l_Name_0)
    local l_ProductID_0 = p_u_24.ProductID
    v_u_4:is_enum_member(l_ProductID_0, v_u_12)
    local l_RobuxCost_0 = p_u_24.RobuxCost
    v_u_4:is_int_greater_than(l_RobuxCost_0, 0)
    local v_u_26
    if p_u_24.CopyFrom == nil then
        v_u_26 = nil
    else
        v_u_4:is_enum_member(p_u_24.CopyFrom, v_u_12)
        v_u_26 = p_u_24.CopyFrom
    end;
    local v_u_27, v_u_28
    if p_u_24.RequiresDayEvent == nil then
        v_u_27 = false
        v_u_28 = 0
    else
        v_u_4:is_enum_member(p_u_24.RequiresDayEvent, v_u_6.EventType)
        v_u_28 = p_u_24.RequiresDayEvent
        v_u_27 = true
    end;
    local v_u_29, v_u_30
    if p_u_24.RequiresDayEventParam2 == nil then
        v_u_29 = false
        v_u_30 = -1
    else
        v_u_4:is_int(p_u_24.RequiresDayEventParam2)
        v_u_30 = p_u_24.RequiresDayEventParam2
        v_u_29 = true
    end;
    local v_u_31 = v_u_5:transparent_assetid()
    if p_u_24.DisplayIcon ~= nil then
        v_u_31 = p_u_24.DisplayIcon
    end;
    v25.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 659 ]]
        --[[ Upvalues: (copy 1): l_Name_0 ]]
        return l_Name_0;
    end;
    v25.get_obj = function(_) --[[ Name: get_obj ]] --[[ Line: 660 ]]
        --[[ Upvalues: (copy 1): p_u_24 ]]
        return p_u_24;
    end;
    v25.get_product_id = function(_) --[[ Name: get_product_id ]] --[[ Line: 661 ]]
        --[[ Upvalues: (copy 1): l_ProductID_0 ]]
        return l_ProductID_0;
    end;
    v25.get_robux_cost = function(_) --[[ Name: get_robux_cost ]] --[[ Line: 662 ]]
        --[[ Upvalues: (copy 1): l_RobuxCost_0 ]]
        return l_RobuxCost_0;
    end;
    v25.requires_day_event = function(_) --[[ Name: requires_day_event ]] --[[ Line: 663 ]]
        --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_28 ]]
        return v_u_27, v_u_28;
    end;
    v25.requires_day_event_param2 = function(_) --[[ Name: requires_day_event_param2 ]] --[[ Line: 664 ]]
        --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_30 ]]
        return v_u_29, v_u_30;
    end;
    v25.get_display_icon = function(_) --[[ Name: get_display_icon ]] --[[ Line: 665 ]]
        --[[ Upvalues: (ref 1): v_u_31 ]]
        return v_u_31;
    end;
    v25.has_copy_from_id = function(_) --[[ Name: has_copy_from_id ]] --[[ Line: 666 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26 ~= nil;
    end;
    v25.get_copy_from_id = function(_) --[[ Name: get_copy_from_id ]] --[[ Line: 667 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26;
    end;
    v25.get_reward_info_list = function(_) --[[ Name: get_reward_info_list ]] --[[ Line: 669 ]]
        --[[ Upvalues: (ref 1): v_u_17, (copy 2): l_ProductID_0 ]]
        return v_u_17:get_reward_info_list_for_purchase_id(l_ProductID_0);
    end;
    v25.get_contents_description = function(p32) --[[ Name: get_contents_description ]] --[[ Line: 670 ]]
        --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_5, (copy 3): l_RobuxCost_0 ]]
        local v33 = v_u_16:generate_only_items_description_from_rewardinfo_list(p32:get_reward_info_list())
        if v_u_5:is_dev_build() and p32:get_reward_info_list():count() >= 1 then
            v33 = v33 .. "\n" .. string.format("Price Each: %.4f", l_RobuxCost_0 / p32:get_reward_info_list():get(1):get_amount())
        end;
        return v33;
    end;
    return v25;
end;
for _, v34 in pairs(v_u_13) do
    v_u_22:add(v34.ProductID, v23:new(v34))
end;
local v_u_35 = v8:new()
for _, v36 in v_u_22:key_itr() do
    if v36:has_copy_from_id() then
        v_u_35:push_back_to(v36:get_copy_from_id(), v36)
    end;
end;
v_u_12.get_id_to_purchase_info_data_dict = function(_) --[[ Name: get_id_to_purchase_info_data_dict ]] --[[ Line: 695 ]]
    --[[ Upvalues: (copy 1): v_u_22 ]]
    return v_u_22;
end;
v_u_12.get_id_to_copy_target_info_data_mdict = function(_) --[[ Name: get_id_to_copy_target_info_data_mdict ]] --[[ Line: 696 ]]
    --[[ Upvalues: (copy 1): v_u_35 ]]
    return v_u_35;
end;
v_u_12.get_info_data_for_productid = function(_, p37) --[[ Name: get_info_data_for_productid ]] --[[ Line: 698 ]]
    --[[ Upvalues: (copy 1): v_u_22, (copy 2): v_u_3 ]]
    if v_u_22:contains(p37) ~= true then
        v_u_3:errf("PurchaseInfo:get_info_data_for_productid(%s) does not contain productid", (tostring(p37)))
    end;
    return v_u_22:get(p37);
end;
v_u_12.get_description_for_productid = function(_, p38) --[[ Name: get_description_for_productid ]] --[[ Line: 705 ]]
    --[[ Upvalues: (copy 1): v_u_22 ]]
    return v_u_22:get(p38):get_contents_description();
end;
v_u_12.get_reward_desc_info_list_for_productid = function(_, p39) --[[ Name: get_reward_desc_info_list_for_productid ]] --[[ Line: 706 ]]
    --[[ Upvalues: (copy 1): v_u_22 ]]
    return v_u_22:get(p39):get_reward_info_list();
end;
v_u_12.productid_requires_day_event = function(_, p40) --[[ Name: productid_requires_day_event ]] --[[ Line: 707 ]]
    --[[ Upvalues: (copy 1): v_u_22 ]]
    return v_u_22:get(p40):requires_day_event();
end;
v_u_12.productid_requires_day_event_param2 = function(_, p41) --[[ Name: productid_requires_day_event_param2 ]] --[[ Line: 708 ]]
    --[[ Upvalues: (copy 1): v_u_22 ]]
    return v_u_22:get(p41):requires_day_event_param2();
end;
v_u_12.sale_combokey_get_songids = function(_, p42) --[[ Name: sale_combokey_get_songids ]] --[[ Line: 712 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2:get_songids_for_saleid(p42);
end;
v_u_12.playerblob_apply_salecombokey = function(_, p43, p44) --[[ Name: playerblob_apply_salecombokey ]] --[[ Line: 716 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): v_u_1 ]]
    local v45 = v_u_12:sale_combokey_get_songids(p44)
    if v45:count() == 0 then
        return false;
    end;
    for v46 = 1, v45:count() do
        v_u_1:add_song(p43, (v45:get(v46)))
    end;
    return true;
end;
v_u_12.get_salecombokey_title = function(_, p47) --[[ Name: get_salecombokey_title ]] --[[ Line: 728 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2:get_title_for_saleid(p47);
end;
v_u_12.get_salecombokey_purchasedescription = function(_, p48) --[[ Name: get_salecombokey_purchasedescription ]] --[[ Line: 732 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2:get_purchased_description_for_saleid(p48);
end;
v_u_12.run_dev_purchase_info_test = function(_) --[[ Name: run_dev_purchase_info_test ]] --[[ Line: 736 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_3, (copy 3): v_u_22, (copy 4): v_u_4 ]]
    if v_u_5:is_dev_build() ~= true then
        return v_u_3:warnf("PurchaseInfo:run_dev_purchase_info_test called when not dev");
    end;
    spawn(function() --[[ Line: 764 ]]
        --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_4, (ref 3): v_u_3 ]]
        local s_MarketplaceService_0 = game:GetService("MarketplaceService")
        for v49, v50 in v_u_22:key_itr() do
            v_u_4:is_true(v49 == v50:get_product_id())
            local l_PriceInRobux_0 = s_MarketplaceService_0:GetProductInfo(v49, Enum.InfoType.Product).PriceInRobux
            if l_PriceInRobux_0 ~= v50:get_robux_cost() then
                v_u_3:warnf("ProductID(%d) local_price(%d) rbx_price(%d)", v49, v50:get_robux_cost(), l_PriceInRobux_0)
            end;
            wait(0.1)
        end;
    end)
end;
return v_u_12;
